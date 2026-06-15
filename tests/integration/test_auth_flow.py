from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User


class AuthFlowIntegrationTest(APITestCase):
    def test_full_auth_flow_static_api_key(self):
        # Create a superuser for the static API key to authenticate as
        User.objects.create_superuser(
            username="admin", email="admin@example.com", password="Password123!"
        )

        api_key = settings.STATIC_API_KEY
        self.client.credentials(HTTP_X_API_KEY=api_key)

        me_url = reverse("user-me")
        response = self.client.get(me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user_data = response.data.get("data", response.data)
        self.assertEqual(user_data["username"], "admin")

    def test_invalid_api_key(self):
        self.client.credentials(HTTP_X_API_KEY="wrong-key")
        me_url = reverse("user-me")
        response = self.client.get(me_url)
        # It seems DRF or the custom exception handler might be returning 403
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )
