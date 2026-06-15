from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from rest_framework import exceptions

from common.authentication import StaticAPIKeyAuthentication

User = get_user_model()


class StaticAPIKeyAuthenticationTests(TestCase):
    def setUp(self):
        self.auth = StaticAPIKeyAuthentication()
        self.factory = RequestFactory()
        self.superuser = User.objects.create_superuser(
            username="admin", password="password", email="admin@example.com"
        )
        self.regular_user = User.objects.create_user(
            username="user1", password="password", email="user1@example.com"
        )
        self.static_key = getattr(settings, "STATIC_API_KEY", "your-default-api-key")

    def test_authenticate_no_header(self):
        request = self.factory.get("/")
        result = self.auth.authenticate(request)
        self.assertIsNone(result)

    def test_authenticate_invalid_key(self):
        request = self.factory.get("/", HTTP_X_API_KEY="invalid-key")
        with self.assertRaises(exceptions.AuthenticationFailed):
            self.auth.authenticate(request)

    def test_authenticate_valid_key_no_test_user(self):
        request = self.factory.get("/", HTTP_X_API_KEY=self.static_key)
        user, auth_token = self.auth.authenticate(request)
        self.assertEqual(user, self.superuser)
        self.assertIsNone(auth_token)

    def test_authenticate_valid_key_with_test_user(self):
        request = self.factory.get(
            "/", HTTP_X_API_KEY=self.static_key, HTTP_X_TEST_USER="user1"
        )
        user, auth_token = self.auth.authenticate(request)
        self.assertEqual(user, self.regular_user)
        self.assertIsNone(auth_token)

    def test_authenticate_test_user_not_found(self):
        request = self.factory.get(
            "/", HTTP_X_API_KEY=self.static_key, HTTP_X_TEST_USER="nonexistent"
        )
        with self.assertRaises(exceptions.AuthenticationFailed):
            self.auth.authenticate(request)
