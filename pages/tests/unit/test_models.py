from django.test import TestCase

from pages.models import Page


class PageModelTest(TestCase):
    def test_page_creation(self):
        page = Page.objects.create(title="About", slug="about", content="content")
        self.assertEqual(str(page), "About")
