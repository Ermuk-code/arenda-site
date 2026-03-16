from django.test import TestCase
from django.contrib.auth import get_user_model

from bookings.models import Booking
from items.models import Item
from .models import Conversation, Message

from datetime import date

User = get_user_model()


class ChatTest(TestCase):

    def setUp(self):

        self.owner = User.objects.create_user(
            username="owner",
            password="123"
        )

        self.renter = User.objects.create_user(
            username="renter",
            password="123"
        )

        self.item = Item.objects.create(
            title="Camera",
            description="Test",
            price_per_day=100,
            owner=self.owner,
            status="available"
        )

        self.booking = Booking.objects.create(
            item=self.item,
            renter=self.renter,
            start_date=date(2026,1,1),
            end_date=date(2026,1,3)
        )

        self.conversation = Conversation.objects.create(
            booking=self.booking
        )

    def test_create_message(self):

        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.renter,
            text="Hello"
        )

        self.assertEqual(message.text, "Hello")