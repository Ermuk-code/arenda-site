import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from datetime import date
from rest_framework.test import APIClient

from .models import Category, Item, ItemImage
from bookings.models import Booking, Review

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


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class ItemEditApiTest(TestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner_edit",
            password="12345",
            email="owner_edit@test.com",
            profile_completed=True
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.owner)
        self.item = Item.objects.create(
            title="Old Camera",
            description="Old description",
            price_per_day=500,
            owner=self.owner,
            status="available"
        )

    def test_owner_can_patch_item_fields(self):
        response = self.client.patch(
            f'/api/items/{self.item.id}/',
            {
                'title': 'New Camera',
                'description': 'Updated description',
                'price_per_day': 700,
            },
            format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.title, 'New Camera')
        self.assertEqual(self.item.description, 'Updated description')
        self.assertEqual(self.item.price_per_day, 700)

    def test_owner_can_upload_new_image_for_existing_item(self):
        image = SimpleUploadedFile(
            "item.jpg",
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
            '/api/items/upload-image/',
            {'item': self.item.id, 'image': image},
            format='multipart'
        )

        self.assertEqual(response.status_code, 201)
        self.item.refresh_from_db()
        self.assertEqual(self.item.images.count(), 1)

    def test_owner_can_delete_existing_image(self):
        image = SimpleUploadedFile(
            "item-delete.jpg",
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
        item_image = ItemImage.objects.create(item=self.item, image=image)

        response = self.client.delete(f'/api/items/images/{item_image.id}/')

        self.assertEqual(response.status_code, 204)
        self.assertFalse(ItemImage.objects.filter(id=item_image.id).exists())


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

    def test_item_detail_includes_booking_reviews(self):
        booking = Booking.objects.create(
            item=self.item,
            renter=self.renter,
            start_date=date(2026, 5, 10),
            end_date=date(2026, 5, 12),
            status='completed',
            payment_status='paid'
        )
        Review.objects.create(
            booking=booking,
            rating=5,
            comment='Отличная аренда'
        )

        response = self.client.get(f'/api/items/{self.item.id}/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['item_reviews']), 1)
        self.assertEqual(response.data['item_reviews'][0]['author_username'], self.renter.username)
        self.assertEqual(response.data['item_reviews'][0]['comment'], 'Отличная аренда')


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
