from django.db import models
from django.conf import settings
from items.models import Item
from django.core.exceptions import ValidationError
from django.db.models import Q


class Booking(models.Model):

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    )

    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name='bookings'
    )

    renter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings'
    )

    start_date = models.DateField()
    end_date = models.DateField()

    total_price = models.DecimalField(
    max_digits=10,
    decimal_places=2,
    blank=True,
    null=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    def clean(self):

        if self.start_date >= self.end_date:
            raise ValidationError("End date must be after start date")

        overlapping = Booking.objects.filter(
            item=self.item,
            status__in=['pending', 'confirmed']
        ).filter(
            Q(start_date__lt=self.end_date) &
            Q(end_date__gt=self.start_date)
        ).exclude(id=self.id)

        if overlapping.exists():
            raise ValidationError("This item is already booked for selected dates")
    def save(self, *args, **kwargs):

        self.clean()

        # Расчёт количества дней
        days = (self.end_date - self.start_date).days

        # Умножаем на цену товара
        self.total_price = days * self.item.price_per_day

        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.item.title} - {self.renter.username}"