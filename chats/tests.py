import tempfile
from datetime import timedelta
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Chat, Message
from items.models import Item

User = get_user_model()


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class ChatTest(TestCase):

    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="123", email="owner@test.com")
        self.renter = User.objects.create_user(username="renter", password="123", email="renter@test.com")
        self.item = Item.objects.create(
            title="Drill",
            description="Tool",
            price_per_day=100,
            owner=self.owner,
            status="available",
        )
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

    def test_create_conversation_is_separated_by_item(self):
        second_item = Item.objects.create(
            title="Saw",
            description="Another tool",
            price_per_day=200,
            owner=self.owner,
            status="available",
        )

        first_response = self.client.post(
            "/api/chats/conversations/",
            {"participant_id": self.owner.id, "item_id": self.item.id},
            format="json",
        )
        second_response = self.client.post(
            "/api/chats/conversations/",
            {"participant_id": self.owner.id, "item_id": second_item.id},
            format="json",
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 201)
        self.assertNotEqual(first_response.json()["id"], second_response.json()["id"])

    def test_conversations_are_sorted_by_last_message(self):
        older_chat = Chat.objects.create(item=self.item)
        older_chat.users.add(self.owner, self.renter)

        newer_item = Item.objects.create(
            title="Camera",
            description="Photo",
            price_per_day=300,
            owner=self.owner,
            status="available",
        )
        newer_chat = Chat.objects.create(item=newer_item)
        newer_chat.users.add(self.owner, self.renter)

        old_message = Message.objects.create(chat=older_chat, sender=self.owner, text="Old")
        new_message = Message.objects.create(chat=newer_chat, sender=self.owner, text="New")

        Message.objects.filter(id=old_message.id).update(created_at=timezone.now() - timedelta(days=1))
        Message.objects.filter(id=new_message.id).update(created_at=timezone.now())

        response = self.client.get("/api/chats/conversations/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        ids = [item["id"] for item in payload]
        self.assertLess(ids.index(newer_chat.id), ids.index(older_chat.id))
