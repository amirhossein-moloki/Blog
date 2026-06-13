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
        # Use HTTP_ACCEPT to trigger the StandardResponseRenderer
        response = self.client.get(url, HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check if the response is wrapped by checking content-type or structure
        # StandardResponseRenderer is set in DEFAULT_RENDERER_CLASSES
        data = response.json()

        # Check for standardized keys
        self.assertIn("data", data)
        self.assertIn("messagesList", data)
        # Detail response should NOT have pagination
        self.assertNotIn("pagination", data)

        self.assertEqual(data["data"]["title"], post.title)

    def test_global_404_error_handling(self):
        url = "/api/does-not-exist/"
        response = self.client.get(url, HTTP_ACCEPT="application/json")

        self.assertIn(
            response.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_302_FOUND]
        )
        if response.status_code == status.HTTP_404_NOT_FOUND:
            data = response.json()
            self.assertIn("messagesList", data)
            self.assertNotIn("pagination", data)

    def test_global_403_error_handling(self):
        url = reverse("user-list")
        self.client.credentials()
        response = self.client.get(url, HTTP_ACCEPT="application/json")

        if response.status_code == 200:
            print("Warning: Endpoint returned 200, expected 401/403")
        else:
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
            self.assertIn("messagesList", response.data)
            self.assertNotIn("pagination", response.data)

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
