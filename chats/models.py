from django.db import models
from django.conf import settings
from bookings.models import Booking

class Conversation(models.Model):

    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name='conversation'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat for booking {self.booking.id}"
class Message(models.Model):

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    text = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Message from {self.sender.username}"