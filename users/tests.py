from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class UserModelTest(TestCase):

    def test_create_user(self):

        user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )

        self.assertEqual(user.username, "testuser")
        self.assertFalse(user.profile_completed)

    def test_string_representation(self):

        user = User.objects.create_user(
            username="testuser",
            password="123"
        )

        self.assertEqual(str(user), user.username)