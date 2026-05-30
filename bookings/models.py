from django.db import models
from django.conf import settings
from items.models import Item
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db.models import Avg
from notifications.models import Notification


class Booking(models.Model):

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    )

    RENT_TYPE_CHOICES = (
        ('hourly', 'Почасовая'),
        ('daily', 'Посуточная'),
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

    # 🔥 НОВОЕ
    rent_type = models.CharField(
        max_length=10,
        choices=RENT_TYPE_CHOICES
    )

    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

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

    # ------------------------
    # ✅ ВАЛИДАЦИЯ
    # ------------------------
    def clean(self):

        if self.item.owner == self.renter:
            raise ValidationError("You cannot book your own item")

        if self.start_date >= self.end_date:
            raise ValidationError("End date must be after start date")

        # 💥 проверка доступности типа аренды
        if self.rent_type == 'hourly' and not self.item.price_per_hour:
            raise ValidationError("Item does not support hourly rent")

        if self.rent_type == 'daily' and not self.item.price_per_day:
            raise ValidationError("Item does not support daily rent")

        # 💥 пересечение дат
        overlapping = Booking.objects.filter(
            item=self.item,
            status__in=['pending', 'confirmed']
        ).filter(
            Q(start_date__lt=self.end_date) &
            Q(end_date__gt=self.start_date)
        ).exclude(id=self.id)

        if overlapping.exists():
            raise ValidationError("This item is already booked")

    # ------------------------
    # 💰 РАСЧЁТ ЦЕНЫ
    # ------------------------
    def calculate_price(self):

        duration = self.end_date - self.start_date

        if self.rent_type == 'hourly':
            hours = duration.total_seconds() / 3600
            base_price = hours * float(self.item.price_per_hour)

        elif self.rent_type == 'daily':
            days = duration.days
            if duration.seconds > 0:
                days += 1  # округляем вверх
            base_price = days * float(self.item.price_per_day)

        # 💥 ИТОГО
        total = (
            base_price +
            float(self.item.deposit) +
            float(self.item.delivery_price)
        )

        return total

    # ------------------------
    # 💾 SAVE
    # ------------------------
    def save(self, *args, **kwargs):

        self.clean()

        # 💰 считаем цену
        self.total_price = self.calculate_price()

        is_new = self.pk is None

        super().save(*args, **kwargs)

        # 🔔 уведомления только при создании
        if is_new:
            from notifications.models import Notification

            Notification.objects.create(
                user=self.item.owner,
                type='booking_created',
                message=f"New booking for {self.item.title}"
            )

    # ------------------------
    # 🔄 СМЕНА СТАТУСА
    # ------------------------
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

        self.status = new_status
        self.save()

        # 🔔 уведомления
        from notifications.models import Notification

        if new_status == 'confirmed':
            Notification.objects.create(
                user=self.renter,
                type='booking_confirmed',
                message=f"Booking confirmed for {self.item.title}"
            )

        if new_status == 'cancelled':
            Notification.objects.create(
                user=self.renter,
                type='booking_cancelled',
                message=f"Booking cancelled"
            )

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
        Notification.objects.create(
            user=self.booking.item.owner,
            type='new_review',
            message="You received a new review"
        )
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