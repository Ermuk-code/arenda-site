import uuid
from datetime import timedelta

from django.db import models
from django.conf import settings
from django.utils import timezone
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
    PAYMENT_METHOD_CHOICES = (
        ('sbp', 'SBP'),
    )
    PAYMENT_STATUS_CHOICES = (
        ('unpaid', 'Unpaid'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
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
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='sbp'
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='unpaid'
    )
    payment_reference = models.UUIDField(
        unique=True,
        null=True,
        blank=True
    )
    payment_expires_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

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
        if new_status == 'completed' and self.payment_status != 'paid':
            raise ValidationError("Booking must be paid before completion")

        previous_status = self.status
        self.status = new_status
        self.save()
        if previous_status != new_status:
            if new_status == 'confirmed':
                notify_booking_confirmed(self)
            elif new_status == 'cancelled':
                cancelled_by = getattr(self, '_status_changed_by', None) or self.renter
                notify_booking_cancelled(self, cancelled_by)

    def start_sbp_payment(self):
        if self.status != 'confirmed':
            raise ValidationError("Payment is available only for confirmed bookings")
        if self.payment_status == 'paid':
            raise ValidationError("Booking is already paid")

        now = timezone.now()
        if (
            self.payment_status == 'pending'
            and self.payment_reference
            and self.payment_expires_at
            and self.payment_expires_at > now
        ):
            return self.get_sbp_payment_payload()

        self.payment_method = 'sbp'
        self.payment_status = 'pending'
        self.payment_reference = uuid.uuid4()
        self.payment_expires_at = now + timedelta(minutes=15)
        self.paid_at = None
        self.save(
            update_fields=[
                'payment_method',
                'payment_status',
                'payment_reference',
                'payment_expires_at',
                'paid_at',
            ]
        )
        return self.get_sbp_payment_payload()

    def confirm_sbp_payment(self):
        if self.status != 'confirmed':
            raise ValidationError("Payment confirmation is available only for confirmed bookings")
        if self.payment_status == 'paid':
            raise ValidationError("Booking is already paid")
        if self.payment_status != 'pending' or not self.payment_reference:
            raise ValidationError("Start SBP payment before confirmation")

        now = timezone.now()
        if self.payment_expires_at and self.payment_expires_at <= now:
            self.payment_status = 'failed'
            self.save(update_fields=['payment_status'])
            raise ValidationError("Payment session expired, start a new one")

        self.payment_status = 'paid'
        self.paid_at = now
        self.payment_expires_at = None
        self.save(update_fields=['payment_status', 'paid_at', 'payment_expires_at'])

    def get_sbp_payment_payload(self):
        if not self.payment_reference:
            raise ValidationError("Payment session not created")

        return {
            'provider': 'sbp_stub',
            'booking_id': self.id,
            'payment_method': self.payment_method,
            'payment_status': self.payment_status,
            'payment_reference': str(self.payment_reference),
            'amount': str(self.total_price),
            'currency': 'RUB',
            'expires_at': self.payment_expires_at.isoformat() if self.payment_expires_at else None,
            'bank_name': 'Demo Bank',
            'recipient': 'OOO Arenda Demo',
            'phone_number': '+79991234567',
            'deeplink': f'sbp://pay?ref={self.payment_reference}&amount={self.total_price}',
            'qr_payload': (
                f'STUB|SBP|booking={self.id}|ref={self.payment_reference}|'
                f'amount={self.total_price}|currency=RUB'
            ),
        }

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
