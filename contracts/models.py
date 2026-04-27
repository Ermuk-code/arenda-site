import uuid
from io import BytesIO
from pathlib import Path
from textwrap import wrap

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from bookings.models import Booking


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
        return f'AR-{self.booking_id or "NEW"}-{uuid.uuid4().hex[:8].upper()}'

    def build_preview_text(self):
        owner = self.booking.item.owner
        renter = self.booking.renter

        renter_signature = 'не подписан'
        if self.renter_signed_at:
            renter_signature = (
                f'{self.renter_signer_name or renter.username}, '
                f'{self.renter_signed_at:%d.%m.%Y %H:%M}, '
                f'код {self.renter_signature_code or "—"}'
            )

        owner_signature = 'не подписан'
        if self.owner_signed_at:
            owner_signature = (
                f'{self.owner_signer_name or owner.username}, '
                f'{self.owner_signed_at:%d.%m.%Y %H:%M}, '
                f'код {self.owner_signature_code or "—"}'
            )

        return (
            f'ДОГОВОР АРЕНДЫ № {self.document_number}\n\n'
            f'Предмет аренды: {self.booking.item.title}\n'
            f'Арендодатель: {owner.username} ({owner.email or "email не указан"})\n'
            f'Арендатор: {renter.username} ({renter.email or "email не указан"})\n'
            f'Период аренды: {self.booking.start_date} — {self.booking.end_date}\n'
            f'Сумма аренды: {self.booking.total_price} RUB\n'
            f'Статус брони: {self.booking.status}\n\n'
            f'Условия:\n'
            f'1. Арендодатель передает вещь во временное пользование арендатору.\n'
            f'2. Арендатор обязуется использовать вещь по назначению и вернуть ее в согласованный срок.\n'
            f'3. Подписание ЭЦП в этом интерфейсе является демонстрационным и используется только для показа учебного проекта.\n\n'
            f'Подпись арендатора: {renter_signature}\n'
            f'Подпись арендодателя: {owner_signature}\n'
        )

    def ensure_generated_file(self):
        content = self.build_preview_text()
        filename = f'contract_{self.booking_id}_{self.document_number}.pdf'
        self.file.save(filename, ContentFile(self.build_pdf_bytes(content)), save=False)
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

        self.save(
            update_fields=[
                'renter_signer_name',
                'renter_signature_code',
                'renter_signed_at',
                'owner_signer_name',
                'owner_signature_code',
                'owner_signed_at',
                'is_signed',
                'signed_at',
            ]
        )
        self.ensure_generated_file()

    def generate_signature_code(self, role):
        return f'EDS-DEMO-{role}-{self.booking_id}-{uuid.uuid4().hex[:10].upper()}'

    def build_pdf_bytes(self, content):
        font = self._load_pdf_font(size=28)
        page_width, page_height = 1240, 1754
        margin_x = 90
        margin_y = 90
        line_height = 42
        max_lines_per_page = max(1, (page_height - margin_y * 2) // line_height)

        wrapped_lines = []
        for paragraph in content.splitlines():
            text = paragraph.strip()
            if not text:
                wrapped_lines.append('')
                continue
            wrapped_lines.extend(wrap(text, width=60))

        if not wrapped_lines:
            wrapped_lines = ['']

        pages = []
        for page_start in range(0, len(wrapped_lines), max_lines_per_page):
            page = Image.new('RGB', (page_width, page_height), 'white')
            draw = ImageDraw.Draw(page)
            y = margin_y
            for line in wrapped_lines[page_start:page_start + max_lines_per_page]:
                draw.text((margin_x, y), line, fill='#111111', font=font)
                y += line_height
            pages.append(page)

        buffer = BytesIO()
        first_page, extra_pages = pages[0], pages[1:]
        first_page.save(
            buffer,
            format='PDF',
            save_all=True,
            append_images=extra_pages,
            resolution=150.0
        )
        return buffer.getvalue()

    def _load_pdf_font(self, size):
        font_candidates = [
            Path('C:/Windows/Fonts/arial.ttf'),
            Path('C:/Windows/Fonts/tahoma.ttf'),
            Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
            Path('/usr/share/fonts/dejavu/DejaVuSans.ttf'),
        ]
        for font_path in font_candidates:
            if font_path.exists():
                return ImageFont.truetype(str(font_path), size=size)
        return ImageFont.load_default()
