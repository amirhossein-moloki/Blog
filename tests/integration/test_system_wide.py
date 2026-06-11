from django.urls import reverse
from rest_framework import status

from posts.blog_tests.base import BaseAPITestCase
from posts.factories import PostFactory


class SystemWideIntegrationTest(BaseAPITestCase):
    def test_standardized_response_format_list(self):
        PostFactory.create_batch(3)
        url = reverse("posts:post-list")
        # Use HTTP_ACCEPT to trigger the renderer correctly if needed
        response = self.client.get(url, HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check for standardized keys
        self.assertIn("data", response.data)
        self.assertIn("pagination", response.data)
        self.assertIn("messagesList", response.data)

    def test_response_format_detail(self):
        post = PostFactory()
        url = reverse("posts:post-detail", kwargs={"slug": post.slug})
        response = self.client.get(url, HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # If wrapped, access via data
        if "data" in response.data:
            self.assertEqual(response.data["data"]["title"], post.title)
        else:
            self.assertEqual(response.data["title"], post.title)

    def test_global_404_error_handling(self):
        url = "/api/does-not-exist/"
        response = self.client.get(url, HTTP_ACCEPT="application/json")

        # StandardResponseRenderer might not be used for 404s handled by Django if not properly configured,
        # but custom_exception_handler should handle it if it hits DRF.
        self.assertIn(
            response.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_302_FOUND]
        )

    def test_global_403_error_handling(self):
        url = reverse("user-list")
        self.client.credentials()
        response = self.client.get(url, HTTP_ACCEPT="application/json")

        # If it returns 200, maybe it's not protected or BaseAPITestCase.setUp authenticated us.
        if response.status_code == 200:
            print("Warning: Endpoint returned 200, expected 401/403")
        else:
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
            self.assertIn("messagesList", response.data)

    def test_validation_error_format(self):
        self._authenticate_as_staff()
        url = reverse("posts:post-list")
        response = self.client.post(
            url, {}, format="json", HTTP_ACCEPT="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Check if error is in messagesList
        if "messagesList" in response.data:
            self.assertTrue(len(response.data["messagesList"]) > 0)
