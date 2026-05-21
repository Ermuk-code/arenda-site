import uuid
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Avg, Q
from django.utils import timezone

from items.models import Item
from notifications.services import (
    notify_booking_cancelled,
    notify_booking_confirmed,
    notify_booking_created,
    notify_new_review,
    notify_payment_confirmed,
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
        if self.item.owner == self.renter:
            raise ValidationError("You cannot book your own item")

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
        is_new = self.pk is None

        self.clean()

        # Freeze booking price on creation so later item price changes
        # do not affect already created bookings or payment flows.
        if is_new or self.total_price is None:
            from decimal import Decimal, ROUND_HALF_UP
            MARKUP_RATE = Decimal('0.20')  # наценка платформы 20%
            days = (self.end_date - self.start_date).days
            price_with_markup = (self.item.price_per_day * (1 + MARKUP_RATE)).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            self.total_price = days * price_with_markup

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
        if not self.has_fully_signed_contract():
            raise ValidationError("Both parties must sign the contract with demo EDS before SBP payment")

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

    def get_contract(self):
        from contracts.models import Contract

        contract = getattr(self, 'contract', None)
        if contract is None and self.status in ['confirmed', 'completed']:
            contract = Contract.create_for_booking(self)
        return contract

    def has_renter_signed_contract(self):
        contract = self.get_contract()
        return bool(contract and contract.renter_signed_at)

    def has_fully_signed_contract(self):
        contract = self.get_contract()
        return bool(contract and contract.renter_signed_at and contract.owner_signed_at and contract.is_signed)

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
        notify_payment_confirmed(self)

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
    is_hidden = models.BooleanField(default=False)
    moderation_reason = models.CharField(max_length=255, blank=True)
    moderated_at = models.DateTimeField(null=True, blank=True)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moderated_booking_reviews'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        is_completed = self.booking.status == 'completed'
        is_paid_booking = (
            self.booking.status == 'confirmed' and
            self.booking.payment_status == 'paid'
        )

        if not (is_completed or is_paid_booking):
            raise ValidationError("You can review only paid bookings")

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
            existing_chat = (
                Chat.objects.filter(item=item, users=self.booking.renter)
                .filter(users=owner)
                .first()
            )
            if not existing_chat:
                existing_chat = Chat.objects.create(item=item)
                existing_chat.users.add(self.booking.renter, owner)

        if is_new:
            notify_new_review(self)
        self.update_rating_counters(item=item, owner=owner)

    def delete(self, *args, **kwargs):
        item = self.booking.item
        owner = item.owner
        super().delete(*args, **kwargs)
        self.update_rating_counters(item=item, owner=owner)

    def hide(self, moderated_by=None, reason=''):
        self.is_hidden = True
        self.moderated_by = moderated_by
        self.moderation_reason = (reason or '').strip()
        self.moderated_at = timezone.now()
        self.save(
            update_fields=[
                'is_hidden',
                'moderated_by',
                'moderation_reason',
                'moderated_at',
            ]
        )

    def unhide(self):
        self.is_hidden = False
        self.moderated_by = None
        self.moderation_reason = ''
        self.moderated_at = None
        self.save(
            update_fields=[
                'is_hidden',
                'moderated_by',
                'moderation_reason',
                'moderated_at',
            ]
        )

    @staticmethod
    def update_rating_counters(*, item, owner):
        visible_item_reviews = Review.objects.filter(
            booking__item=item,
            is_hidden=False,
        )
        item.average_rating = visible_item_reviews.aggregate(
            Avg('rating')
        )['rating__avg'] or 0
        item.reviews_count = visible_item_reviews.count()
        item.save(update_fields=['average_rating', 'reviews_count'])

        visible_owner_reviews = Review.objects.filter(
            booking__item__owner=owner,
            is_hidden=False,
        )
        owner.average_rating = visible_owner_reviews.aggregate(
            Avg('rating')
        )['rating__avg'] or 0
        owner.reviews_count = visible_owner_reviews.count()
        owner.save(update_fields=['average_rating', 'reviews_count'])
