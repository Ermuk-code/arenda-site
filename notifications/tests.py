from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from bookings.models import Booking
from chats.models import Chat, Message
from items.models import Item
from notifications.management.commands import Command as LegacyReturnReminderCommand
from notifications.models import Notification
from notifications.services import notify_new_message, notify_payment_confirmed, notify_return_reminder

User = get_user_model()


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class NotificationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner',
            password='12345',
            email='owner@test.com',
            profile_completed=True,
        )
        self.renter = User.objects.create_user(
            username='renter',
            password='12345',
            email='renter@test.com',
            profile_completed=True,
        )
        self.item = Item.objects.create(
            title='Drill',
            description='Power drill',
            price_per_day=1000,
            owner=self.owner,
            status='available',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.owner)

    @patch('notifications.services.send_booking_created')
    def test_booking_creation_creates_owner_notification(self, send_booking_created_mock):
        Booking.objects.create(
            item=self.item,
            renter=self.renter,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 3),
        )

        self.assertTrue(
            Notification.objects.filter(
                user=self.owner,
                type='booking_created',
            ).exists()
        )
        notification = Notification.objects.get(
            user=self.owner,
            type='booking_created',
        )
        self.assertEqual(notification.metadata.get('destination'), 'incoming_bookings')
        self.assertEqual(notification.metadata.get('item_id'), self.item.id)
        send_booking_created_mock.assert_called_once()

    @patch('notifications.services.send_booking_confirmed')
    def test_confirm_booking_creates_renter_notification(self, send_booking_confirmed_mock):
        booking = Booking.objects.create(
            item=self.item,
            renter=self.renter,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 3),
        )

        booking._status_changed_by = self.owner
        booking.change_status('confirmed')

        self.assertTrue(
            Notification.objects.filter(
                user=self.renter,
                type='booking_confirmed',
            ).exists()
        )
        notification = Notification.objects.get(
            user=self.renter,
            type='booking_confirmed',
        )
        self.assertEqual(notification.metadata.get('destination'), 'rent_payment')
        self.assertEqual(notification.metadata.get('item_id'), self.item.id)
        send_booking_confirmed_mock.assert_called_once()

    def test_mark_notification_read_endpoints(self):
        notification = Notification.objects.create(
            user=self.owner,
            type='booking_created',
            message='Test',
        )

        response = self.client.post(f'/api/notifications/{notification.id}/mark_read/')
        self.assertEqual(response.status_code, 200)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    @patch('notifications.services.send_return_reminder')
    def test_return_reminder_creates_notification(self, send_return_reminder_mock):
        booking = Booking.objects.create(
            item=self.item,
            renter=self.renter,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 3),
            status='confirmed',
        )

        notify_return_reminder(booking)

        self.assertTrue(
            Notification.objects.filter(
                user=self.renter,
                type='return_reminder',
            ).exists()
        )
        send_return_reminder_mock.assert_called_once()

    def test_payment_confirmed_notification_points_to_my_items(self):
        booking = Booking.objects.create(
            item=self.item,
            renter=self.renter,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 3),
            status='confirmed',
            payment_status='paid',
        )

        notify_payment_confirmed(booking)

        notification = Notification.objects.get(
            user=self.owner,
            type='payment_confirmed',
        )
        self.assertEqual(notification.metadata.get('destination'), 'my_items')
        self.assertEqual(notification.metadata.get('item_id'), self.item.id)

    @patch('notifications.services.send_payment_confirmed')
    def test_payment_confirmed_sends_email(self, send_payment_confirmed_mock):
        booking = Booking.objects.create(
            item=self.item,
            renter=self.renter,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 3),
            status='confirmed',
            payment_status='paid',
        )

        notify_payment_confirmed(booking)

        send_payment_confirmed_mock.assert_called_once_with(booking)

    @patch('notifications.services.send_new_message')
    def test_new_message_notification_contains_chat_metadata(self, send_new_message_mock):
        chat = Chat.objects.create(item=self.item)
        chat.users.add(self.owner, self.renter)
        message = Message.objects.create(chat=chat, sender=self.renter, text='Здравствуйте')

        notify_new_message(message)

        notification = Notification.objects.get(
            user=self.owner,
            type='new_message',
        )
        self.assertEqual(notification.metadata.get('destination'), 'chat')
        self.assertEqual(notification.metadata.get('chat_id'), chat.id)
        self.assertEqual(notification.metadata.get('item_id'), self.item.id)
        send_new_message_mock.assert_called_once()

    @patch('notifications.services.send_return_reminder')
    def test_legacy_return_reminder_command_creates_correct_notification(self, send_return_reminder_mock):
        tomorrow = timezone.now().date() + timedelta(days=1)
        booking = Booking.objects.create(
            item=self.item,
            renter=self.renter,
            start_date=date(2026, 4, 20),
            end_date=tomorrow,
            status='confirmed',
        )

        LegacyReturnReminderCommand().handle()

        notification = Notification.objects.get(user=self.renter, type='return_reminder')
        self.assertEqual(notification.metadata.get('destination'), 'item')
        self.assertEqual(notification.metadata.get('booking_id'), booking.id)
        self.assertEqual(notification.metadata.get('item_id'), self.item.id)
        send_return_reminder_mock.assert_called_once_with(booking)
