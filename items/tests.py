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
            password="123",
            email="owner@example.com"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

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

    def test_booked_ranges_returns_pending_and_confirmed_bookings(self):
        item = Item.objects.create(
            title="Camera",
            description="DSLR camera",
            price_per_day=100,
            owner=self.user,
            status="available"
        )
        renter = User.objects.create_user(
            username="renter",
            password="123",
            email="renter@example.com",
            profile_completed=True
        )

        Booking.objects.create(
            item=item,
            renter=renter,
            start_date=date(2026, 4, 25),
            end_date=date(2026, 4, 27),
            status="pending"
        )
        cancelled = Booking.objects.create(
            item=item,
            renter=User.objects.create_user(
                username="other",
                password="123",
                email="other@example.com",
                profile_completed=True
            ),
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 3),
            status="pending"
        )
        cancelled.status = "cancelled"
        cancelled.save(update_fields=["status"])

        response = self.client.get(f"/api/items/{item.id}/booked_ranges/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [
            {"from": "2026-04-25", "to": "2026-04-27"}
        ])
