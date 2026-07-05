from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from posts.models import AuthorProfile

User = get_user_model()

class AuthorProfileAPITest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.author = AuthorProfile.objects.create(user=self.user, display_name="Test Author", bio="Old Bio")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = reverse("posts:authorprofile-detail", kwargs={"pk": self.user.id})

    def test_put_requires_mandatory_fields(self):
        """
        EN: PUT requires all mandatory fields to be present.
        FA: متد PUT مستلزم حضور تمام فیلدهای اجباری است.
        """
        # Sending only 'bio' in PUT should fail because 'display_name' and 'user' are missing.
        response = self.client.put(self.url, {"bio": "New Bio"})
        self.assertEqual(response.status_code, 400)
        # StandardResponseRenderer moves errors to messagesList
        error_messages = str(response.data.get("messagesList", []))
        self.assertIn("display_name", error_messages)
        self.assertIn("user", error_messages)

    def test_patch_updates_partially(self):
        """
        EN: PATCH allows updating only a subset of fields.
        FA: متد PATCH اجازه به‌روزرسانی زیرمجموعه‌ای از فیلدها را می‌دهد.
        """
        response = self.client.patch(self.url, {"bio": "New Bio"})
        self.assertEqual(response.status_code, 200)
        self.author.refresh_from_db()
        self.assertEqual(self.author.bio, "New Bio")
        # display_name should remain unchanged
        self.assertEqual(self.author.display_name, "Test Author")

    def test_put_updates_fully(self):
        """
        EN: PUT successfully updates the resource when all mandatory fields are provided.
        FA: متد PUT منبع را با موفقیت به‌روزرسانی می‌کند وقتی تمام فیلدهای اجباری ارائه شوند.
        """
        data = {
            "user": self.user.id,
            "display_name": "Updated Name",
            "bio": "Updated Bio"
        }
        response = self.client.put(self.url, data)
        self.assertEqual(response.status_code, 200, response.data)
        self.author.refresh_from_db()
        self.assertEqual(self.author.display_name, "Updated Name")
        self.assertEqual(self.author.bio, "Updated Bio")
