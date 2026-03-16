from django.test import TestCase
from django.contrib.auth import get_user_model

from .models import Item

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