from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date

from items.models import Item
from .models import Booking
from .models import Review

User = get_user_model()

class BookingModelTest(TestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner',
            password='12345',
            profile_completed=True
        )

        self.renter = User.objects.create_user(
            username='renter',
            password='12345',
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
            start_date=date(2026,1,1),
            end_date=date(2026,1,3),
            status="completed"
        )

        review = Review.objects.create(
            booking=booking,
            rating=5,
            comment="Great!"
        )

        self.assertEqual(review.rating, 5)