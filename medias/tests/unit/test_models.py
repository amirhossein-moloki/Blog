from django.test import TestCase
from django.urls import reverse

from medias.models import Media
from posts.factories import UserFactory


class MediaModelTest(TestCase):
    def test_media_creation(self):
        user = UserFactory()
        media = Media.objects.create(
            storage_key="test.jpg",
            url="http://example.com/test.jpg",
            type="image",
            mime="image/jpeg",
            size_bytes=100,
            uploaded_by=user,
            title="Test Media",
        )
        self.assertEqual(str(media), "Test Media")
        self.assertEqual(
            media.get_download_url(),
            reverse("medias:download_media", kwargs={"media_id": media.pk}),
        )

    def test_media_str_fallback(self):
        media = Media(storage_key="test_key")
        self.assertEqual(str(media), "test_key")
