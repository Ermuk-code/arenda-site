from django.db import models
from django.conf import settings
from items.models import Item
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db.models import Avg
from notifications.services import (
    notify_booking_cancelled,
    notify_booking_confirmed,
    notify_booking_created,
    notify_new_review,
)


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

        # Нельзя бронировать свой товар
        if self.item.owner == self.renter:
            raise ValidationError("You cannot book your own item")

        # Дата окончания должна быть позже начала
        if self.start_date >= self.end_date:
            raise ValidationError("End date must be after start date")

        # Проверка пересечения дат
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
        is_new = self.pk is None

        self.clean()

        # Расчёт количества дней
        days = (self.end_date - self.start_date).days

        # Умножаем на цену товара
        self.total_price = days * self.item.price_per_day
        super().save(*args, **kwargs)
        if is_new:
            notify_booking_created(self)
    def change_status(self, new_status):

        allowed_transitions = {
            'pending': ['confirmed', 'cancelled'],
            'confirmed': ['completed', 'cancelled'],
            'cancelled': [],
            'completed': [],
        }

        if new_status not in allowed_transitions[self.status]:
            raise ValidationError(
                f"Cannot change status from {self.status} to {new_status}"
            )

        previous_status = self.status
        self.status = new_status
        self.save()
        if previous_status != new_status:
            if new_status == 'confirmed':
                notify_booking_confirmed(self)
            elif new_status == 'cancelled':
                cancelled_by = getattr(self, '_status_changed_by', None) or self.renter
                notify_booking_cancelled(self, cancelled_by)
    def __str__(self):
        return f"{self.item.title} - {self.renter.username}"
class Review(models.Model):

    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name='review'
    )

    rating = models.IntegerField()
    comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):

        if self.booking.status != 'completed':
            raise ValidationError("You can review only completed bookings")

        if not (1 <= self.rating <= 5):
            raise ValidationError("Rating must be between 1 and 5")

    def save(self, *args, **kwargs):
        from chats.models import Chat
        is_new = self.pk is None
        self.clean()
        super().save(*args, **kwargs)

        item = self.booking.item
        owner = item.owner
        if self.booking.status == 'confirmed':
            Chat.objects.get_or_create(booking=self)
        # ---- рейтинг товара ----
        item_reviews = Review.objects.filter(
            booking__item=item
        )
        if is_new:
            notify_new_review(self)
        item.average_rating = item_reviews.aggregate(
            Avg('rating')
        )['rating__avg'] or 0

        item.reviews_count = item_reviews.count()
        item.save()

        # ---- рейтинг владельца ----
        owner_reviews = Review.objects.filter(
            booking__item__owner=owner
        )

        owner.average_rating = owner_reviews.aggregate(
            Avg('rating')
        )['rating__avg'] or 0

        owner.reviews_count = owner_reviews.count()
        owner.save()
