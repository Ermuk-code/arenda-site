from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


class UserModelTest(TestCase):

    def setUp(self):
        self.client = APIClient()

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

    def test_profile_endpoint_returns_and_updates_identity_fields(self):
        user = User.objects.create_user(
            username="profile_user",
            password="testpass123",
            email="profile@example.com",
            user_type="individual"
        )
        self.client.force_authenticate(user=user)

        response = self.client.get("/api/users/profile/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["username"], "profile_user")
        self.assertEqual(response.json()["email"], "profile@example.com")

        update_response = self.client.put(
            "/api/users/profile/",
            {
                "username": "updated_user",
                "email": "updated@example.com",
                "user_type": "individual",
                "passport_series": "1234",
                "passport_number": "123456",
                "inn": "123456789012"
            },
            format="json"
        )

        self.assertEqual(update_response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.username, "updated_user")
        self.assertEqual(user.email, "updated@example.com")
        self.assertTrue(user.profile_completed)
