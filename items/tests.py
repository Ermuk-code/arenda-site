from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date
from rest_framework.test import APIClient

from .models import Category, Item
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


class ItemCategoryApiTest(TestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner_categories",
            password="12345",
            email="owner_categories@test.com",
            profile_completed=True
        )
        self.category_tools = Category.objects.create(name="Инструменты")
        self.category_sport = Category.objects.create(name="Спорт")
        self.tools_item = Item.objects.create(
            title="Drill",
            description="Power drill",
            price_per_day=700,
            owner=self.owner,
            status="available",
            category=self.category_tools
        )
        Item.objects.create(
            title="Bike",
            description="Mountain bike",
            price_per_day=1200,
            owner=self.owner,
            status="available",
            category=self.category_sport
        )
        self.client = APIClient()

    def test_categories_endpoint_returns_categories(self):
        response = self.client.get('/api/items/categories/')

        self.assertEqual(response.status_code, 200)
        returned_names = [item['name'] for item in response.data['results']]
        self.assertIn("Инструменты", returned_names)
        self.assertIn("Спорт", returned_names)

    def test_items_can_be_filtered_by_category(self):
        response = self.client.get(f'/api/items/?category={self.category_tools.id}')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.tools_item.id)
