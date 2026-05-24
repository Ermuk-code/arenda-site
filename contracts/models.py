import uuid
from decimal import Decimal
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone

from bookings.models import Booking

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ---------------------------------------------------------------------------
# Font registration — called inside build_pdf_bytes to survive Django workers
# ---------------------------------------------------------------------------
_FONT_CANDIDATES = [
    (
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf',
        'DejaVu', 'DejaVuBold', 'DejaVuItalic',
    ),
    (
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        'Liberation', 'LiberationBold', 'LiberationItalic',
    ),
    (
        '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
        '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf',
        '/usr/share/fonts/truetype/freefont/FreeSansOblique.ttf',
        'FreeSans', 'FreeSansBold', 'FreeSansItalic',
    ),
]

import os as _os

def _ensure_cyrillic_fonts():
    """Register a Cyrillic-capable TTF font set and return (normal, bold, italic) names.
    Re-registers every call so it's safe across Django worker processes.
    """
    for reg_path, bold_path, italic_path, name, bold_name, italic_name in _FONT_CANDIDATES:
        if not _os.path.exists(reg_path):
            continue
        try:
            pdfmetrics.registerFont(TTFont(name, reg_path))
            pdfmetrics.registerFont(TTFont(bold_name, bold_path if _os.path.exists(bold_path) else reg_path))
            pdfmetrics.registerFont(TTFont(italic_name, italic_path if _os.path.exists(italic_path) else reg_path))
            return name, bold_name, italic_name
        except Exception:
            continue
    # absolute fallback — no Cyrillic, but won't crash
    return 'Helvetica', 'Helvetica-Bold', 'Helvetica-Oblique'


# ---------------------------------------------------------------------------
# Helper: build party description from user object
# ---------------------------------------------------------------------------
def _party_description(user):
    """
    Returns (party_line, requisites_dict) depending on user_type.
    party_line  — text for header 'именуемый в дальнейшем…'
    requisites  — dict with keys: label, inn, kpp, ogrn, passport, full_name
    """
    utype = getattr(user, 'user_type', 'individual')

    if utype == 'individual':
        full_name = (user.full_name or user.username).strip()
        series = getattr(user, 'passport_series', '') or ''
        number = getattr(user, 'passport_number', '') or ''
        passport_str = f'паспорт: серия {series} № {number}' if series or number else ''
        inn = getattr(user, 'inn', '') or ''

        if passport_str:
            party_line = f'{full_name} ({passport_str})'
        else:
            party_line = full_name

        requisites = {
            'label': full_name,
            'type': 'individual',
            'full_name': full_name,
            'passport': f'{series} {number}'.strip() if series or number else '—',
            'inn': inn or '—',
            'kpp': '—',
            'ogrn': '—',
            'signer_prefix': '',   # у физлица не пишем "в лице"
        }

    elif utype == 'entrepreneur':
        ent_name = (user.entrepreneur_name or user.full_name or user.username).strip()
        full_name = (user.full_name or user.username).strip()
        inn = getattr(user, 'inn', '') or ''
        ogrnip = getattr(user, 'ogrnip', '') or ''

        party_line = f'{ent_name}'
        requisites = {
            'label': ent_name,
            'type': 'entrepreneur',
            'full_name': full_name,
            'passport': '—',
            'inn': inn or '—',
            'kpp': '—',
            'ogrn': ogrnip or '—',
            'signer_prefix': full_name,
        }

    else:  # legal
        company_name = (user.company_name or user.username).strip()
        full_name = (user.full_name or user.username).strip()
        inn = getattr(user, 'inn', '') or ''
        kpp = getattr(user, 'kpp', '') or ''
        ogrnip = getattr(user, 'ogrnip', '') or ''

        party_line = f'{company_name}'
        requisites = {
            'label': company_name,
            'type': 'legal',
            'full_name': full_name,
            'passport': '—',
            'inn': inn or '—',
            'kpp': kpp or '—',
            'ogrn': ogrnip or '—',
            'signer_prefix': full_name,
        }

    return party_line, requisites


def _eds_block(signer_name, signed_at, signature_code, role_label):
    """Returns a formatted EDS stamp string."""
    if signed_at and signature_code:
        date_str = signed_at.strftime('%d.%m.%Y %H:%M')
        return (
            f'ДОКУМЕНТ ПОДПИСАН ЭЛЕКТРОННОЙ ПОДПИСЬЮ\n'
            f'Подписант ({role_label}): {signer_name}\n'
            f'Дата подписания: {date_str}\n'
            f'Код подписи: {signature_code}'
        )
    return 'Место для ЭЦП\n(не подписан)'


# ---------------------------------------------------------------------------
# Main Contract model
# ---------------------------------------------------------------------------
class Contract(models.Model):
    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name='contract'
    )
    document_number = models.CharField(max_length=64, unique=True, editable=False)
    file = models.FileField(upload_to='contracts/', blank=True)
    is_signed = models.BooleanField(default=False)
    renter_signer_name = models.CharField(max_length=255, blank=True)
    renter_signature_code = models.CharField(max_length=128, blank=True)
    renter_signed_at = models.DateTimeField(null=True, blank=True)
    owner_signer_name = models.CharField(max_length=255, blank=True)
    owner_signature_code = models.CharField(max_length=128, blank=True)
    owner_signed_at = models.DateTimeField(null=True, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.document_number:
            self.document_number = self.generate_document_number()
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.file:
            self.ensure_generated_file()

    def __str__(self):
        return f'Contract {self.document_number} for booking #{self.booking_id}'

    @classmethod
    def create_for_booking(cls, booking):
        contract, _ = cls.objects.get_or_create(booking=booking)
        contract.ensure_generated_file()
        return contract

    def generate_document_number(self):
        year = timezone.now().year
        short_id = uuid.uuid4().hex[:6].upper()
        return f'AR-{year}-{self.booking_id or "NEW"}-{short_id}'

    # ------------------------------------------------------------------
    # Preview text (used in frontend contract modal)
    # ------------------------------------------------------------------
    def build_preview_text(self):
        booking = self.booking
        owner = booking.item.owner
        renter = booking.renter

        _, owner_req = _party_description(owner)
        _, renter_req = _party_description(renter)

        owner_sig = _eds_block(
            self.owner_signer_name or owner.username,
            self.owner_signed_at,
            self.owner_signature_code,
            'Арендодатель'
        )
        renter_sig = _eds_block(
            self.renter_signer_name or renter.username,
            self.renter_signed_at,
            self.renter_signature_code,
            'Арендатор'
        )

        # Rent amount without deposit
        deposit = booking.deposit_amount or Decimal('0')
        total = booking.total_price or Decimal('0')
        rent_only = total - deposit

        lines = [
            f'ДОГОВОР БРОНИРОВАНИЯ № {self.document_number}',
            '',
            f'Дата: {booking.created_at.strftime("%d.%m.%Y") if booking.created_at else "—"}',
            '',
            '─' * 60,
            '',
            f'Предмет аренды: {booking.item.title}',
            f'Период:         {booking.start_date} — {booking.end_date}',
            f'Сумма аренды:   {rent_only} руб.',
            f'Залог:          {deposit} руб.',
            '',
            f'Арендодатель: {owner_req["label"]}',
            f'Арендатор:    {renter_req["label"]}',
            '',
            '═' * 60,
            '',
            '  АРЕНДОДАТЕЛЬ                   АРЕНДАТОР',
            '',
        ]
        # Pad each sig block side-by-side
        os_lines = owner_sig.splitlines()
        rs_lines = renter_sig.splitlines()
        max_lines = max(len(os_lines), len(rs_lines))
        for i in range(max_lines):
            ol = os_lines[i] if i < len(os_lines) else ''
            rl = rs_lines[i] if i < len(rs_lines) else ''
            lines.append(f'  {ol:<38}{rl}')

        return '\n'.join(lines)

    def ensure_generated_file(self):
        pdf_bytes = self.build_pdf_bytes()
        filename = f'contract_{self.booking_id}_{self.document_number}.pdf'
        self.file.save(filename, ContentFile(pdf_bytes), save=False)
        super().save(update_fields=['file'])

    def can_be_opened(self):
        return self.booking.status in ['confirmed', 'completed']

    def sign_for_user(self, user, signer_name, certificate_pin):
        if not self.can_be_opened():
            raise ValidationError('Contract is available only for confirmed or completed bookings')

        signer_name = (signer_name or '').strip()
        certificate_pin = (certificate_pin or '').strip()

        if len(signer_name) < 3:
            raise ValidationError('Signer name is too short')
        if len(certificate_pin) < 4:
            raise ValidationError('Signature PIN must contain at least 4 characters')

        now = timezone.now()
        if user == self.booking.renter:
            if self.renter_signed_at:
                raise ValidationError('Renter has already signed this contract')
            self.renter_signer_name = signer_name
            self.renter_signature_code = self.generate_signature_code('RENTER')
            self.renter_signed_at = now
        elif user == self.booking.item.owner:
            if self.owner_signed_at:
                raise ValidationError('Owner has already signed this contract')
            self.owner_signer_name = signer_name
            self.owner_signature_code = self.generate_signature_code('OWNER')
            self.owner_signed_at = now
        else:
            raise ValidationError('Only booking participants can sign the contract')

        if self.renter_signed_at and self.owner_signed_at:
            self.is_signed = True
            self.signed_at = now

        self.save(update_fields=[
            'renter_signer_name', 'renter_signature_code', 'renter_signed_at',
            'owner_signer_name', 'owner_signature_code', 'owner_signed_at',
            'is_signed', 'signed_at',
        ])
        self.ensure_generated_file()

    def generate_signature_code(self, role):
        return f'EDS-DEMO-{role}-{self.booking_id}-{uuid.uuid4().hex[:10].upper()}'

    # ------------------------------------------------------------------
    # PDF generation — matches the uploaded template exactly
    # ------------------------------------------------------------------
    def build_pdf_bytes(self):
        BASE_FONT, BOLD_FONT, ITALIC_FONT = _ensure_cyrillic_fonts()
        booking = self.booking
        owner = booking.item.owner
        renter = booking.renter

        owner_party, owner_req = _party_description(owner)
        renter_party, renter_req = _party_description(renter)

        # Rent amount without deposit
        deposit = booking.deposit_amount or Decimal('0')
        total = booking.total_price or Decimal('0')
        rent_only = total - deposit

        # Dates
        contract_date = (booking.created_at or timezone.now()).strftime('%d.%m.%Y')
        start_date = str(booking.start_date) if booking.start_date else '—'
        end_date = str(booking.end_date) if booking.end_date else '—'

        # Party header lines per user type
        def party_header(party_line, req, role_name, signer_name_field):
            if req['type'] == 'individual':
                return f'{party_line}, именуемый(ая) в дальнейшем {role_name}'
            else:
                signer = signer_name_field or req['full_name']
                return (
                    f'{party_line}, в лице {signer}, '
                    f'именуемый(ая) в дальнейшем {role_name}'
                )

        owner_header = party_header(owner_party, owner_req, 'Арендодатель', self.owner_signer_name)
        renter_header = party_header(renter_party, renter_req, 'Арендатор', self.renter_signer_name)

        # ── Build PDF ──────────────────────────────────────────────────
        buffer = BytesIO()

        PAGE_W, PAGE_H = A4
        margin_left = 20 * mm
        margin_right = 20 * mm
        margin_top = 20 * mm
        margin_bottom = 20 * mm
        content_width = PAGE_W - margin_left - margin_right

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=margin_left,
            rightMargin=margin_right,
            topMargin=margin_top,
            bottomMargin=margin_bottom,
        )

        # Styles
        _ss = getSampleStyleSheet()
        def S(name, parent='Normal', **kw):
            base = {
                'fontName': BASE_FONT,
                'fontSize': 10,
                'leading': 14,
                'textColor': colors.HexColor('#111111'),
            }
            base.update(kw)
            return ParagraphStyle(name, parent=_ss.get(parent, _ss['Normal']), **base)

        sTitle = S('title', fontName=BOLD_FONT, fontSize=14, alignment=TA_CENTER, spaceBefore=0, spaceAfter=4)
        sDate = S('date', fontSize=10, alignment=TA_CENTER, spaceAfter=12, textColor=colors.HexColor('#555555'))
        sHeader = S('header', fontSize=10, alignment=TA_JUSTIFY, spaceAfter=10, leading=15)
        sSectionTitle = S('sec', fontName=BOLD_FONT, fontSize=10, spaceBefore=10, spaceAfter=4)
        sBody = S('body', fontSize=10, alignment=TA_JUSTIFY, spaceAfter=4, leading=14)
        sBold = S('bold', fontName=BOLD_FONT, fontSize=10, spaceAfter=4)
        sSmall = S('small', fontSize=9, textColor=colors.HexColor('#444444'), spaceAfter=2)
        sEds = S('eds', fontName=BOLD_FONT, fontSize=9, textColor=colors.HexColor('#1a3e4c'),
                 backColor=colors.HexColor('#e8f5f2'), alignment=TA_CENTER, spaceAfter=2, leading=13)
        sEdsCode = S('edsCode', fontSize=8, textColor=colors.HexColor('#2b6a7c'),
                     alignment=TA_CENTER, spaceAfter=0, leading=12)
        sEdsUnsigned = S('edsUnsigned', fontSize=9, textColor=colors.HexColor('#999999'),
                         alignment=TA_CENTER, spaceAfter=2, leading=13)

        story = []

        # ── Title ──────────────────────────────────────────────────────
        story.append(Paragraph(f'ДОГОВОР БРОНИРОВАНИЯ № {self.document_number}', sTitle))
        story.append(Paragraph(f'«{contract_date}»', sDate))

        # ── Parties header ─────────────────────────────────────────────
        story.append(Paragraph(
            f'{owner_header} и {renter_header}, '
            f'вместе именуемые Стороны, а по отдельности — Сторона, '
            f'заключили настоящий договор проката (далее — Договор) о нижеследующем:',
            sHeader
        ))

        story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#ccd8e0')))
        story.append(Spacer(1, 6))

        # Helper to add section
        def section(number, title, items):
            story.append(Paragraph(f'{number}. {title}', sSectionTitle))
            for item in items:
                story.append(Paragraph(item, sBody))

        # ── 1. Предмет договора ────────────────────────────────────────
        story.append(Paragraph('1. ПРЕДМЕТ ДОГОВОРА', sSectionTitle))
        story.append(Paragraph(
            f'1.1. Арендодатель обязуется предоставить Арендатору за плату во временное '
            f'владение и пользование следующее движимое имущество (далее — Имущество): '
            f'<b>{booking.item.title}</b>.',
            sBody
        ))
        story.append(Paragraph(
            f'1.2. Стоимость аренды Имущества по настоящему Договору составляет '
            f'<b>{rent_only} ({self._amount_words(rent_only)}) руб.</b>',
            sBody
        ))
        story.append(Paragraph(
            '1.3. Арендодатель знакомит Арендатора с правилами эксплуатации или выдаёт '
            'инструкцию по пользованию Имуществом.',
            sBody
        ))
        story.append(Paragraph(
            '1.4. На момент заключения настоящего Договора Имущество принадлежит '
            'Арендодателю на праве собственности, не является предметом залога или '
            'имущественного спора с третьими лицами.',
            sBody
        ))

        # ── 2. Срок действия ───────────────────────────────────────────
        story.append(Paragraph('2. СРОК ДЕЙСТВИЯ ДОГОВОРА', sSectionTitle))
        story.append(Paragraph(
            f'2.1. Договор вступает в силу с «{start_date}» и действует до «{end_date}».',
            sBody
        ))

        # ── 3. Права и обязанности ─────────────────────────────────────
        story.append(Paragraph('3. ПРАВА И ОБЯЗАННОСТИ СТОРОН', sSectionTitle))
        story.append(Paragraph('3.1. Арендатор имеет право:', sBold))
        for item in [
            '— требовать уменьшения арендной платы, если условия пользования или состояние Имущества существенно ухудшились не по его вине;',
            '— досрочно прекратить исполнение Договора, уведомив Арендодателя за 5 (Пять) рабочих дней и возвратив арендуемое Имущество по акту приёма-передачи.',
        ]:
            story.append(Paragraph(item, sBody))

        story.append(Paragraph('3.2. Арендатор обязан:', sBold))
        for item in [
            '— своевременно вносить арендную плату за пользование Имуществом;',
            '— обеспечить сохранность Имущества с момента его приёма и до момента возврата Арендодателю;',
            '— пользоваться Имуществом в соответствии с условиями настоящего Договора;',
            '— при прекращении Договора вернуть Арендодателю Имущество в надлежащем состоянии;',
            '— своевременно уведомлять Арендодателя о повреждении Имущества.',
        ]:
            story.append(Paragraph(item, sBody))

        story.append(Paragraph('3.3. Арендодатель имеет право:', sBold))
        for item in [
            '— осуществлять проверку состояния Имущества не чаще 1 (Одного) раза в месяц;',
            '— контролировать целевое использование Арендатором переданного в аренду Имущества.',
        ]:
            story.append(Paragraph(item, sBody))

        story.append(Paragraph('3.4. Арендодатель обязан:', sBold))
        for item in [
            '— предоставить Арендатору Имущество в состоянии, пригодном для использования;',
            '— письменно уведомить Арендатора обо всех скрытых дефектах Имущества до его передачи;',
            '— своевременно устранять недостатки Имущества, препятствующие его нормальному использованию.',
        ]:
            story.append(Paragraph(item, sBody))

        # ── 4. Порядок передачи ────────────────────────────────────────
        story.append(Paragraph('4. ПОРЯДОК ПЕРЕДАЧИ ИМУЩЕСТВА', sSectionTitle))
        story.append(Paragraph(
            '4.1. Передача Арендатору Имущества в аренду и его возврат Арендодателю '
            'оформляются двусторонними актами приёма-передачи, подписываемыми Сторонами.',
            sBody
        ))

        # ── 5. Арендная плата ──────────────────────────────────────────
        story.append(Paragraph('5. АРЕНДНАЯ ПЛАТА И ПОРЯДОК РАСЧЁТОВ', sSectionTitle))
        story.append(Paragraph(
            f'5.1. За пользование Имуществом Арендатор оплачивает арендную плату в размере '
            f'<b>{rent_only} руб.</b> за весь период аренды.',
            sBody
        ))
        story.append(Paragraph(
            '5.2. Оплата производится безналичным платежом по реквизитам через платёжную платформу.',
            sBody
        ))
        story.append(Paragraph(
            '5.3. В случае досрочного возврата Арендатором Имущества Арендодатель производит '
            'пересчёт суммы арендной платы за время фактического использования Имущества.',
            sBody
        ))

        # ── 6. Изменение и прекращение ─────────────────────────────────
        story.append(Paragraph('6. ИЗМЕНЕНИЕ И ПРЕКРАЩЕНИЕ ДОГОВОРА', sSectionTitle))
        story.append(Paragraph(
            '6.1. По соглашению Сторон настоящий Договор может быть изменён или расторгнут.',
            sBody
        ))

        # ── 7. Ответственность ─────────────────────────────────────────
        story.append(Paragraph('7. ОТВЕТСТВЕННОСТЬ СТОРОН', sSectionTitle))
        story.append(Paragraph(
            '7.1. В случае неисполнения или ненадлежащего исполнения обязательств по '
            'настоящему Договору Стороны несут ответственность в соответствии с Договором '
            'и действующим законодательством РФ.',
            sBody
        ))

        # ── 8. Разрешение споров ───────────────────────────────────────
        story.append(Paragraph('8. РАЗРЕШЕНИЕ СПОРОВ', sSectionTitle))
        story.append(Paragraph(
            '8.1. Споры Стороны стремятся разрешать путём переговоров в течение 20 '
            '(Двадцати) рабочих дней. Неурегулированные споры разрешаются в судебном порядке.',
            sBody
        ))

        # ── 9. Прочие условия ──────────────────────────────────────────
        story.append(Paragraph('9. ПРОЧИЕ УСЛОВИЯ', sSectionTitle))
        story.append(Paragraph(
            '9.1. Любые изменения и дополнения к настоящему Договору должны быть оформлены '
            'в письменном виде и подписаны обеими Сторонами.',
            sBody
        ))
        story.append(Paragraph(
            '9.2. Настоящий Договор составлен и подписан в двух экземплярах, по одному '
            'экземпляру для каждой из Сторон.',
            sBody
        ))
        story.append(Paragraph(
            '9.3. Во всём остальном, что не предусмотрено настоящим Договором, Стороны '
            'руководствуются действующим гражданским законодательством РФ.',
            sBody
        ))

        story.append(Spacer(1, 10))
        story.append(HRFlowable(width='100%', thickness=0.8, color=colors.HexColor('#2b6a7c')))
        story.append(Spacer(1, 6))

        # ── 10. Реквизиты ──────────────────────────────────────────────
        story.append(Paragraph('10. РЕКВИЗИТЫ И ПОДПИСИ СТОРОН', sSectionTitle))

        # Requisites table
        col_w = content_width / 2 - 2 * mm

        def req_rows(req):
            rows = [('Наименование / ФИО:', req['label'])]
            if req['type'] == 'individual':
                rows.append(('Паспорт:', req['passport']))
            else:
                rows.append(('ИНН:', req['inn']))
                if req['kpp'] != '—':
                    rows.append(('КПП:', req['kpp']))
                rows.append(('ОГРН/ОГРНИП:', req['ogrn']))
            return rows

        owner_rows = req_rows(owner_req)
        renter_rows = req_rows(renter_req)
        max_rows = max(len(owner_rows), len(renter_rows))

        # Pad shorter side
        while len(owner_rows) < max_rows:
            owner_rows.append(('', ''))
        while len(renter_rows) < max_rows:
            renter_rows.append(('', ''))

        # Build table: [owner_key, owner_val, renter_key, renter_val]
        req_table_data = [
            [Paragraph('<b>Арендодатель</b>', sBold), '', Paragraph('<b>Арендатор</b>', sBold), ''],
        ]
        for (ok, ov), (rk, rv) in zip(owner_rows, renter_rows):
            req_table_data.append([
                Paragraph(ok, sSmall), Paragraph(ov, sSmall),
                Paragraph(rk, sSmall), Paragraph(rv, sSmall),
            ])

        cw = content_width / 4
        req_table = Table(req_table_data, colWidths=[cw * 0.7, cw * 1.3, cw * 0.7, cw * 1.3])
        req_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), BASE_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.HexColor('#ccd8e0')),
            ('SPAN', (0, 0), (1, 0)),
            ('SPAN', (2, 0), (3, 0)),
            ('ALIGN', (0, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (3, 0), 'CENTER'),
        ]))
        story.append(req_table)
        story.append(Spacer(1, 10))

        # ── EDS blocks ─────────────────────────────────────────────────
        half = content_width / 2 - 3 * mm

        def eds_cell(signer_name, signed_at, code, role_label):
            inner = []
            if signed_at and code:
                date_str = signed_at.strftime('%d.%m.%Y %H:%M')
                inner.append(Paragraph('✅ ДОКУМЕНТ ПОДПИСАН\nЭЛЕКТРОННОЙ ПОДПИСЬЮ', sEds))
                inner.append(Paragraph(f'Подписант: {signer_name}', sEdsCode))
                inner.append(Paragraph(f'Дата: {date_str}', sEdsCode))
                inner.append(Paragraph(f'Код подписи: {code}', sEdsCode))
            else:
                inner.append(Paragraph(f'Место для ЭЦП\n({role_label})', sEdsUnsigned))
            return inner

        owner_eds = eds_cell(
            self.owner_signer_name or owner.username,
            self.owner_signed_at, self.owner_signature_code, 'Арендодатель'
        )
        renter_eds = eds_cell(
            self.renter_signer_name or renter.username,
            self.renter_signed_at, self.renter_signature_code, 'Арендатор'
        )

        eds_table = Table(
            [[owner_eds, renter_eds]],
            colWidths=[half, half],
        )
        eds_table.setStyle(TableStyle([
            ('BOX', (0, 0), (0, 0), 0.8, colors.HexColor('#2b6a7c')),
            ('BOX', (1, 0), (1, 0), 0.8, colors.HexColor('#2b6a7c')),
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#f0f8fb')),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#f0f8fb')),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(eds_table)

        # ── Footer note ────────────────────────────────────────────────
        story.append(Spacer(1, 8))
        story.append(Paragraph(
            f'Договор № {self.document_number} сформирован автоматически платформой Arenda. '
            f'Подписание производится демонстрационной ЭЦП для целей учебного проекта.',
            sSmall
        ))

        doc.build(story)
        return buffer.getvalue()

    @staticmethod
    def _amount_words(amount):
        """Very basic amount-to-words stub (returns formatted number)."""
        try:
            n = int(amount)
            return f'{n:,}'.replace(',', ' ')
        except Exception:
            return str(amount)
