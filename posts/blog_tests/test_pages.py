from django.urls import reverse
from rest_framework import status

from posts.blog_tests.base import BaseAPITestCase
from posts.factories import PageFactory


class PageAPITest(BaseAPITestCase):
    def test_create_page(self):
        self._authenticate_as_staff()
        url = reverse("pages:page-list")
        data = {"title": "New Page", "slug": "new-page", "content": "Some content."}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_list_pages(self):
        PageFactory.create_batch(3)
        url = reverse("pages:page-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
