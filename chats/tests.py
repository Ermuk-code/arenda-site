from django.test import TestCase
from django.contrib.auth import get_user_model
from items.models import Item
from .models import Chat, Message

User = get_user_model()

class ChatTest(TestCase):

    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="123", email="owner@test.com")
        self.renter = User.objects.create_user(username="renter", password="123", email="renter@test.com")
        self.chat = Chat.objects.create()
        self.chat.users.add(self.owner, self.renter)

    def test_create_message(self):
        message = Message.objects.create(chat=self.chat, sender=self.renter, text="Hello")
        self.assertEqual(message.text, "Hello")

    def test_chat_members(self):
        self.assertIn(self.owner, self.chat.users.all())
        self.assertIn(self.renter, self.chat.users.all())