from django.db import models
from bookings.models import Booking
from contracts.utils import generate_contract_pdf


class Contract(models.Model):

    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE
    )

    file = models.FileField(upload_to='contracts/')

    # 👇 НОВОЕ
    signed_by_renter = models.BooleanField(default=False)
    signed_by_owner = models.BooleanField(default=False)

    is_signed = models.BooleanField(default=False)

    signed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

def save(self, *args, **kwargs):

    is_new = self.pk is None
    super().save(*args, **kwargs)

    # 📄 генерируем PDF только при создании
    if is_new and not self.file:
        pdf_path = generate_contract_pdf(self)
        self.file = pdf_path
        super().save(update_fields=['file'])