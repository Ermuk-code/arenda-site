from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date
from rest_framework.test import APIClient

from .models import Item
from bookings.models import Booking

User = get_user_model()


class ItemModelTest(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            username="owner",
            password="123"
        )

    def test_create_item(self):

        item = Item.objects.create(
            title="Camera",
            description="DSLR camera",
            price_per_day=100,
            owner=self.user,
            status="available"
        )

        self.assertEqual(item.title, "Camera")
        self.assertEqual(item.owner, self.user)


class ItemApiBookingRangesTest(TestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner_api",
            password="12345",
            email="owner_api@test.com",
            profile_completed=True
        )
        self.renter = User.objects.create_user(
            username="renter_api",
            password="12345",
            email="renter_api@test.com",
            profile_completed=True
        )
        self.item = Item.objects.create(
            title="Projector",
            description="Portable projector",
            price_per_day=500,
            owner=self.owner,
            status="available"
        )
        self.client = APIClient()

    def test_item_list_includes_booked_ranges(self):
        Booking.objects.create(
            item=self.item,
            renter=self.renter,
            start_date=date(2026, 5, 10),
            end_date=date(2026, 5, 12),
            status='confirmed'
        )

        response = self.client.get('/api/items/')

        self.assertEqual(response.status_code, 200)
        item_data = response.data['results'][0]
        self.assertEqual(
            item_data['booked_ranges'],
            [{'start_date': '2026-05-10', 'end_date': '2026-05-12'}]
        )

    def test_booked_ranges_endpoint_returns_active_ranges_only(self):
        Booking.objects.create(
            item=self.item,
            renter=self.renter,
            start_date=date(2026, 5, 10),
            end_date=date(2026, 5, 12),
            status='pending'
        )
        Booking.objects.create(
            item=self.item,
            renter=self.renter,
            start_date=date(2026, 5, 15),
            end_date=date(2026, 5, 18),
            status='cancelled'
        )

        response = self.client.get(f'/api/items/{self.item.id}/booked_ranges/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            [{'start_date': '2026-05-10', 'end_date': '2026-05-12'}]
        )
