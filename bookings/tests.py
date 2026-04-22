from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from chats.models import Chat
from items.models import Item

from .models import Booking, Review

User = get_user_model()


class BookingModelTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner',
            password='12345',
            email='owner_model@test.com',
            profile_completed=True
        )
        self.renter = User.objects.create_user(
            username='renter',
            password='12345',
            email='renter_model@test.com',
            profile_completed=True
        )
        self.item = Item.objects.create(
            title="Drill",
            description="Power drill",
            price_per_day=1000,
            owner=self.owner,
            status='available'
        )

    def test_booking_total_price_calculation(self):
        booking = Booking.objects.create(
            item=self.item,
            renter=self.renter,
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 4)
        )

        self.assertEqual(booking.total_price, 3000)

    def test_cannot_book_own_item(self):
        with self.assertRaises(Exception):
            Booking.objects.create(
                item=self.item,
                renter=self.owner,
                start_date=date(2025, 6, 1),
                end_date=date(2025, 6, 3)
            )

    def test_booking_date_overlap(self):
        Booking.objects.create(
            item=self.item,
            renter=self.renter,
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 5)
        )

        with self.assertRaises(Exception):
            Booking.objects.create(
                item=self.item,
                renter=self.renter,
                start_date=date(2025, 6, 3),
                end_date=date(2025, 6, 7)
            )

    def test_create_review(self):
        booking = Booking.objects.create(
            item=self.item,
            renter=self.renter,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 3),
            status="completed"
        )

        review = Review.objects.create(
            booking=booking,
            rating=5,
            comment="Great!"
        )

        self.assertEqual(review.rating, 5)

    def test_total_price_is_fixed_after_item_price_change(self):
        booking = Booking.objects.create(
            item=self.item,
            renter=self.renter,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 4)
        )

        self.item.price_per_day = 2000
        self.item.save()

        booking.status = 'confirmed'
        booking.save()
        booking.refresh_from_db()

        self.assertEqual(booking.total_price, 3000)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class BookingApiTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner_api',
            password='12345',
            email='owner@test.com',
            profile_completed=True
        )
        self.renter = User.objects.create_user(
            username='renter_api',
            password='12345',
            email='renter@test.com',
            profile_completed=True
        )
        self.item = Item.objects.create(
            title='Camera',
            description='Mirrorless camera',
            price_per_day=1500,
            owner=self.owner,
            status='available'
        )
        self.owner_client = APIClient()
        self.owner_client.force_authenticate(user=self.owner)
        self.renter_client = APIClient()
        self.renter_client.force_authenticate(user=self.renter)

    def create_booking(self):
        return Booking.objects.create(
            item=self.item,
            renter=self.renter,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 3)
        )

    def test_owner_sees_incoming_bookings_in_list(self):
        booking = self.create_booking()

        response = self.owner_client.get('/api/bookings/?role=incoming')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], booking.id)

    def test_booking_cannot_be_updated_via_patch(self):
        booking = self.create_booking()

        response = self.renter_client.patch(
            f'/api/bookings/{booking.id}/',
            {'end_date': '2026-05-04'},
            format='json'
        )

        self.assertEqual(response.status_code, 405)

    def test_owner_can_confirm_booking(self):
        booking = self.create_booking()

        response = self.owner_client.post(f'/api/bookings/{booking.id}/confirm/')

        self.assertEqual(response.status_code, 200)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'confirmed')

    def test_renter_can_cancel_booking(self):
        booking = self.create_booking()
        booking._status_changed_by = self.owner
        booking.change_status('confirmed')

        response = self.renter_client.post(f'/api/bookings/{booking.id}/cancel/')

        self.assertEqual(response.status_code, 200)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'cancelled')

    def test_owner_can_complete_booking(self):
        booking = self.create_booking()
        booking._status_changed_by = self.owner
        booking.change_status('confirmed')
        booking.start_sbp_payment()
        booking.confirm_sbp_payment()

        response = self.owner_client.post(f'/api/bookings/{booking.id}/complete/')

        self.assertEqual(response.status_code, 200)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'completed')

    def test_renter_can_leave_review_after_completion(self):
        booking = self.create_booking()
        booking._status_changed_by = self.owner
        booking.change_status('confirmed')
        booking.start_sbp_payment()
        booking.confirm_sbp_payment()
        booking._status_changed_by = self.owner
        booking.change_status('completed')

        response = self.renter_client.post(
            f'/api/bookings/{booking.id}/review/',
            {'rating': 5, 'comment': 'Great rental'},
            format='json'
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Review.objects.filter(booking=booking).exists())

    def test_renter_can_leave_review_for_paid_finished_confirmed_booking(self):
        today = timezone.localdate()
        booking = Booking.objects.create(
            item=self.item,
            renter=self.renter,
            start_date=today - timedelta(days=3),
            end_date=today - timedelta(days=1),
        )
        booking._status_changed_by = self.owner
        booking.change_status('confirmed')
        booking.start_sbp_payment()
        booking.confirm_sbp_payment()

        response = self.renter_client.post(
            f'/api/bookings/{booking.id}/review/',
            {'rating': 5, 'comment': 'Paid and finished'},
            format='json'
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Review.objects.filter(booking=booking).exists())
        self.assertTrue(
            Chat.objects.filter(item=self.item, users=self.owner)
            .filter(users=self.renter)
            .exists()
        )

    def test_renter_can_start_sbp_payment(self):
        booking = self.create_booking()
        booking._status_changed_by = self.owner
        booking.change_status('confirmed')

        response = self.renter_client.post(f'/api/bookings/{booking.id}/start_payment/')

        self.assertEqual(response.status_code, 200)
        booking.refresh_from_db()
        self.assertEqual(booking.payment_status, 'pending')
        self.assertEqual(response.data['provider'], 'sbp_stub')
        self.assertEqual(response.data['booking_id'], booking.id)
        self.assertIn('qr_payload', response.data)

    def test_payment_cannot_start_before_confirmation(self):
        booking = self.create_booking()

        response = self.renter_client.post(f'/api/bookings/{booking.id}/start_payment/')

        self.assertEqual(response.status_code, 400)
        booking.refresh_from_db()
        self.assertEqual(booking.payment_status, 'unpaid')

    def test_renter_can_confirm_sbp_payment(self):
        booking = self.create_booking()
        booking._status_changed_by = self.owner
        booking.change_status('confirmed')
        booking.start_sbp_payment()

        response = self.renter_client.post(f'/api/bookings/{booking.id}/confirm_payment/')

        self.assertEqual(response.status_code, 200)
        booking.refresh_from_db()
        self.assertEqual(booking.payment_status, 'paid')
        self.assertIsNotNone(booking.paid_at)

    def test_complete_requires_paid_booking(self):
        booking = self.create_booking()
        booking._status_changed_by = self.owner
        booking.change_status('confirmed')

        response = self.owner_client.post(f'/api/bookings/{booking.id}/complete/')

        self.assertEqual(response.status_code, 400)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'confirmed')

    def test_payment_amount_keeps_original_booking_price_after_item_update(self):
        booking = self.create_booking()
        original_total_price = booking.total_price

        self.item.price_per_day = 3000
        self.item.save()

        booking._status_changed_by = self.owner
        booking.change_status('confirmed')

        response = self.renter_client.post(f'/api/bookings/{booking.id}/start_payment/')

        self.assertEqual(response.status_code, 200)
        booking.refresh_from_db()
        self.assertEqual(booking.total_price, original_total_price)
        self.assertEqual(response.data['amount'], str(booking.total_price))
