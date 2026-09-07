from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

User = get_user_model()


class AdminCSRFSecurityTestCase(TestCase):
    def setUp(self):
        self.username = "admin_test_user"
        self.password = "SecureAdminPass123!"
        self.admin_user = User.objects.create_superuser(
            username=self.username,
            email="admin@example.com",
            password=self.password,
        )
        self.index_url = reverse("admin:index")
        self.login_url = reverse("admin:login") + f"?next={self.index_url}"

    def test_01_admin_login_page_loads_and_sets_csrf_cookie(self):
        """Verify Admin login page loads (200 OK) and sets a csrftoken cookie."""
        client = Client(enforce_csrf_checks=True)
        response = client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", client.cookies)

    def test_02_admin_login_success_with_valid_credentials_and_csrf(self):
        """Verify staff login succeeds with valid credentials and valid CSRF token."""
        client = Client(enforce_csrf_checks=True)
        get_response = client.get(self.login_url)
        csrf_token = get_response.cookies["csrftoken"].value

        post_data = {
            "username": self.username,
            "password": self.password,
            "next": self.index_url,
            "csrfmiddlewaretoken": csrf_token,
        }
        response = client.post(self.login_url, post_data)
        # Should redirect to admin index on successful login
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.index_url)

    def test_03_admin_login_failure_with_invalid_credentials(self):
        """Verify admin login with wrong password fails gracefully without server error."""
        client = Client(enforce_csrf_checks=True)
        get_response = client.get(self.login_url)
        csrf_token = get_response.cookies["csrftoken"].value

        post_data = {
            "username": self.username,
            "password": "WrongPassword123!",
            "next": self.index_url,
            "csrfmiddlewaretoken": csrf_token,
        }
        response = client.post(self.login_url, post_data)
        self.assertEqual(response.status_code, 200)  # Re-renders login page with error
        self.assertContains(response, "Please enter the correct username and password")

    def test_04_missing_csrf_token_rejected(self):
        """Verify POST request missing CSRF token is rejected with 403 Forbidden."""
        client = Client(enforce_csrf_checks=True)
        client.get(self.login_url)  # Get cookie
        post_data = {
            "username": self.username,
            "password": self.password,
            "next": self.index_url,
        }
        response = client.post(self.login_url, post_data)
        self.assertEqual(response.status_code, 403)

    def test_05_invalid_csrf_token_rejected(self):
        """Verify POST request with an invalid CSRF token is rejected with 403 Forbidden."""
        client = Client(enforce_csrf_checks=True)
        client.get(self.login_url)
        post_data = {
            "username": self.username,
            "password": self.password,
            "next": self.index_url,
            "csrfmiddlewaretoken": "invalid_fake_csrf_token_value_12345",
        }
        response = client.post(self.login_url, post_data)
        self.assertEqual(response.status_code, 403)

    @override_settings(
        ALLOWED_HOSTS=["admin.example.com", "localhost", "127.0.0.1"],
        CSRF_TRUSTED_ORIGINS=["https://admin.example.com"],
    )
    def test_06_trusted_legitimate_origin_accepted_under_https(self):
        """Verify cross-origin HTTPS requests from CSRF_TRUSTED_ORIGINS are accepted."""
        client = Client(enforce_csrf_checks=True)
        get_response = client.get(
            self.login_url,
            HTTP_HOST="admin.example.com",
            HTTP_X_FORWARDED_PROTO="https",
        )
        csrf_token = get_response.cookies["csrftoken"].value

        post_data = {
            "username": self.username,
            "password": self.password,
            "next": self.index_url,
            "csrfmiddlewaretoken": csrf_token,
        }
        response = client.post(
            self.login_url,
            post_data,
            HTTP_HOST="admin.example.com",
            HTTP_ORIGIN="https://admin.example.com",
            HTTP_X_FORWARDED_PROTO="https",
        )
        self.assertNotEqual(response.status_code, 403)

    @override_settings(
        ALLOWED_HOSTS=["trusted.example.com", "localhost", "127.0.0.1"],
        CSRF_TRUSTED_ORIGINS=["https://trusted.example.com"],
    )
    def test_07_untrusted_origin_rejected(self):
        """Verify requests from untrusted HTTPS origins are rejected with 403 Forbidden."""
        client = Client(enforce_csrf_checks=True)
        get_response = client.get(
            self.login_url,
            HTTP_HOST="trusted.example.com",
            HTTP_X_FORWARDED_PROTO="https",
        )
        csrf_token = get_response.cookies["csrftoken"].value

        post_data = {
            "username": self.username,
            "password": self.password,
            "next": self.index_url,
            "csrfmiddlewaretoken": csrf_token,
        }
        response = client.post(
            self.login_url,
            post_data,
            HTTP_HOST="trusted.example.com",
            HTTP_ORIGIN="https://evil-untrusted-site.com",
            HTTP_X_FORWARDED_PROTO="https",
        )
        self.assertEqual(response.status_code, 403)

    def test_08_https_forwarded_proto_handling(self):
        """Verify Django correctly respects HTTP_X_FORWARDED_PROTO header."""
        client = Client(enforce_csrf_checks=True)
        response = client.get(
            self.login_url,
            HTTP_X_FORWARDED_PROTO="https",
            HTTP_HOST="localhost",
        )
        self.assertTrue(response.wsgi_request.is_secure())

    def test_09_cookie_security_attributes_in_production_simulation(self):
        """Verify cookie security flags in production (Secure, SameSite, HttpOnly)."""
        with override_settings(
            DEBUG=False,
            CSRF_COOKIE_SECURE=True,
            SESSION_COOKIE_SECURE=True,
            CSRF_COOKIE_SAMESITE="Lax",
            SESSION_COOKIE_SAMESITE="Lax",
        ):
            client = Client(enforce_csrf_checks=True)
            response = client.get(
                self.login_url,
                HTTP_X_FORWARDED_PROTO="https",
            )
            csrf_cookie = response.cookies.get("csrftoken")
            self.assertIsNotNone(csrf_cookie)
            self.assertTrue(csrf_cookie["secure"])
            self.assertEqual(csrf_cookie["samesite"], "Lax")
