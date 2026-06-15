from django.conf import settings
from rest_framework.test import APITestCase

from posts.factories import UserFactory
from posts.models import AuthorProfile


class BaseAPITestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.author_profile, _ = AuthorProfile.objects.get_or_create(
            user=self.user, defaults={"display_name": self.user.username}
        )
        self.staff_user = UserFactory(is_staff=True, is_superuser=True)
        self.staff_author_profile, _ = AuthorProfile.objects.get_or_create(
            user=self.staff_user, defaults={"display_name": self.staff_user.username}
        )

    def tearDown(self):
        super().tearDown()

    def _authenticate(self, user=None):
        # EN: Use Static API Key and X-Test-User for authentication in tests
        # FA: استفاده از کلید API ثابت و X-Test-User برای احراز هویت در تست‌ها
        user_to_auth = user or self.user
        api_key = settings.STATIC_API_KEY
        self.client.credentials(
            HTTP_X_API_KEY=api_key, HTTP_X_TEST_USER=user_to_auth.username
        )

    def _authenticate_as_staff(self):
        self._authenticate(self.staff_user)
