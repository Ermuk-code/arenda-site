from django.db import models
from bookings.models import Booking


class Contract(models.Model):

    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE
    )

    file = models.FileField(upload_to='contracts/')

    is_signed = models.BooleanField(default=False)

    signed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)