import tempfile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from .models import Chat, Message

User = get_user_model()


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class ChatTest(TestCase):

    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="123", email="owner@test.com")
        self.renter = User.objects.create_user(username="renter", password="123", email="renter@test.com")
        self.chat = Chat.objects.create()
        self.chat.users.add(self.owner, self.renter)
        self.client = APIClient()
        self.client.force_authenticate(user=self.renter)

    def test_create_message(self):
        message = Message.objects.create(chat=self.chat, sender=self.renter, text="Hello")
        self.assertEqual(message.text, "Hello")

    def test_chat_members(self):
        self.assertIn(self.owner, self.chat.users.all())
        self.assertIn(self.renter, self.chat.users.all())

    def test_create_message_with_image_via_api(self):
        image = SimpleUploadedFile(
            "chat.jpg",
            (
                b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
                b"\xff\xdb\x00C\x00" + b"\x08" * 64 +
                b"\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01"
                b"\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08"
                b"\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                b"\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00?\x00\xd2\xcf \xff\xd9"
            ),
            content_type="image/jpeg",
        )

        response = self.client.post(
            f"/api/chats/conversations/{self.chat.id}/messages/",
            {"text": "", "image": image},
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Message.objects.count(), 1)
        self.assertTrue(Message.objects.first().image.name.startswith("chat_images/"))

    def test_create_empty_message_via_api_is_rejected(self):
        response = self.client.post(
            f"/api/chats/conversations/{self.chat.id}/messages/",
            {"text": "   "},
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Message.objects.count(), 0)

    def test_support_faq_is_available_without_auth(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/api/chats/support-faq/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("questions", payload)
        self.assertGreaterEqual(len(payload["questions"]), 5)

    def test_mark_read_returns_updated_message_ids(self):
        unread_message = Message.objects.create(chat=self.chat, sender=self.owner, text="Unread")

        response = self.client.post(f"/api/chats/conversations/{self.chat.id}/mark_read/")

        self.assertEqual(response.status_code, 200)
        unread_message.refresh_from_db()
        self.assertTrue(unread_message.is_read)
        self.assertEqual(response.json()["message_ids"], [unread_message.id])
