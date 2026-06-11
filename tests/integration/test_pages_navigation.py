from django.urls import reverse
from rest_framework import status

from posts.blog_tests.base import BaseAPITestCase
from posts.factories import MenuFactory, MenuItemFactory


class PagesNavigationIntegrationTest(BaseAPITestCase):
    def test_page_lifecycle(self):
        # 1. Create page as admin
        self._authenticate_as_staff()
        url = reverse("pages:page-list")
        data = {
            "title": "New Page",
            "slug": "new-page",
            "content": "Page content",
            "status": "published",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 2. List pages as guest
        self.client.credentials()
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # StandardResponseRenderer should have wrapped it for list views
        if "data" in response.data and isinstance(response.data["data"], list):
            pages = response.data["data"]
        else:
            pages = response.data

        self.assertTrue(any(page["slug"] == "new-page" for page in pages))

    def test_navigation_menu_structure(self):
        self._authenticate_as_staff()
        menu = MenuFactory(location="header", name="Main Menu")
        MenuItemFactory(menu=menu, label="Home", url="/", order=1)

        url = reverse("navigation:menu-detail", kwargs={"pk": menu.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if "data" in response.data:
            menu_data = response.data["data"]
        else:
            menu_data = response.data

        self.assertEqual(menu_data["name"], "Main Menu")

    def test_unauthorized_page_creation(self):
        self._authenticate()  # Regular user, not staff
        url = reverse("pages:page-list")
        data = {"title": "Hack", "slug": "hack", "content": "hack"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
