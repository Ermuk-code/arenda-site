from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


class Notification(models.Model):

    NOTIFICATION_TYPES = (
        ('booking_created', 'Новая заявка на аренду'),
        ('booking_confirmed', 'Бронирование подтверждено'),
        ('booking_cancelled', 'Бронирование отменено'),
        ('payment_confirmed', 'Оплата подтверждена'),
        ('return_reminder', 'Напоминание о возврате'),
        ('new_message', 'Новое сообщение'),
        ('new_review', 'Новый отзыв'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES
    )

    message = models.TextField()

    metadata = models.JSONField(default=dict, blank=True)

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.type}"
