from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from django.conf import settings
import os


def generate_contract_pdf(contract):
    booking = contract.booking
    item = booking.item
    renter = booking.renter
    owner = item.owner

    filename = f"contract_{contract.id}.pdf"
    filepath = os.path.join(settings.MEDIA_ROOT, 'contracts', filename)

    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    doc = SimpleDocTemplate(filepath)
    styles = getSampleStyleSheet()

    content = []

    content.append(Paragraph("ДОГОВОР АРЕНДЫ", styles['Title']))
    content.append(Spacer(1, 20))

    content.append(Paragraph(f"Арендодатель: {owner.username}", styles['Normal']))
    content.append(Paragraph(f"Арендатор: {renter.username}", styles['Normal']))
    content.append(Spacer(1, 10))

    content.append(Paragraph(f"Предмет аренды: {item.title}", styles['Normal']))
    content.append(Paragraph(f"Описание: {item.description}", styles['Normal']))
    content.append(Spacer(1, 10))

    content.append(Paragraph(f"Дата начала: {booking.start_date}", styles['Normal']))
    content.append(Paragraph(f"Дата окончания: {booking.end_date}", styles['Normal']))
    content.append(Spacer(1, 10))

    content.append(Paragraph(f"Итого: {booking.total_price} ₽", styles['Normal']))
    content.append(Spacer(1, 20))

    content.append(Paragraph("Подписи сторон:", styles['Heading2']))
    content.append(Spacer(1, 10))

    content.append(Paragraph("Арендодатель: ____________", styles['Normal']))
    content.append(Paragraph("Арендатор: ____________", styles['Normal']))

    doc.build(content)

    return f"contracts/{filename}"