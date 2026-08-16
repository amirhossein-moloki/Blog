from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status

from posts.blog_tests.base import BaseAPITestCase
from posts.factories import (
    AuthorProfileFactory,
    CategoryFactory,
    GalleryItemFactory,
    MediaFactory,
    PodcastCategoryFactory,
    PodcastFactory,
)
from posts.models import (
    AuthorProfile,
    Category,
    GalleryItem,
    Podcast,
    PodcastCategory,
)


class HybridMediaEndpointsAPITest(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self._authenticate_as_staff()

        # URLs
        self.podcasts_url = reverse("posts:podcast-list")
        self.gallery_url = reverse("posts:galleryitem-list")
        self.categories_url = reverse("posts:category-list")
        self.podcast_categories_url = reverse("posts:podcastcategory-list")
        self.authors_url = reverse("posts:authorprofile-list")

        # Dummy valid image/audio files
        self.valid_image = SimpleUploadedFile(
            name="test_image.jpg",
            content=b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b",
            content_type="image/jpeg",
        )
        self.valid_audio = SimpleUploadedFile(
            name="test_audio.mp3",
            content=b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\x00" * 200,
            content_type="audio/mpeg",
        )

    # --- Podcasts Tests ---

    def test_podcast_direct_file_upload(self):
        """Test creating a podcast via direct file uploads for cover and audio."""
        cat = PodcastCategoryFactory()
        payload = {
            "title": "Direct File Podcast",
            "slug": "direct-file-podcast",
            "category": cat.pk,
            "episode_number": 1,
            "cover_image": self.valid_image,
            "audio_file": self.valid_audio,
            "media_type": "audio",
            "duration": 25,
            "published_date": "2026-08-16T10:00:00Z",
        }
        response = self.client.post(self.podcasts_url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data["cover_image"])
        self.assertIsNotNone(response.data["audio_file"])

        podcast = Podcast.objects.get(slug="direct-file-podcast")
        self.assertIsNotNone(podcast.cover_image)
        self.assertIsNotNone(podcast.audio_file)

    def test_podcast_media_id_upload(self):
        """Test creating a podcast using existing Media IDs."""
        cat = PodcastCategoryFactory()
        cover_media = MediaFactory()
        audio_media = MediaFactory()

        payload = {
            "title": "Media ID Podcast",
            "slug": "media-id-podcast",
            "category": cat.pk,
            "episode_number": 2,
            "cover_image_id": cover_media.id,
            "audio_file_id": audio_media.id,
            "media_type": "audio",
            "duration": 30,
            "published_date": "2026-08-16T10:00:00Z",
        }
        response = self.client.post(self.podcasts_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["cover_image"]["id"], cover_media.id)
        self.assertEqual(response.data["audio_file"]["id"], audio_media.id)

    def test_podcast_invalid_media_id(self):
        """Test sending non-existent Media ID returns validation error."""
        cat = PodcastCategoryFactory()
        payload = {
            "title": "Invalid ID Podcast",
            "slug": "invalid-id-podcast",
            "category": cat.pk,
            "episode_number": 3,
            "cover_image_id": 999999,
            "duration": 15,
            "published_date": "2026-08-16T10:00:00Z",
        }
        response = self.client.post(self.podcasts_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_podcast_simultaneous_id_and_file_rejection(self):
        """Test submitting both file and ID for cover_image raises validation error."""
        cat = PodcastCategoryFactory()
        cover_media = MediaFactory()

        payload = {
            "title": "Conflicting Podcast",
            "slug": "conflicting-podcast",
            "category": cat.pk,
            "episode_number": 4,
            "cover_image": self.valid_image,
            "cover_image_id": cover_media.id,
            "duration": 10,
            "published_date": "2026-08-16T10:00:00Z",
        }
        response = self.client.post(self.podcasts_url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            any("cover_image" in msg for msg in response.data.get("messagesList", []))
            or "cover_image" in response.data
        )

    # --- Gallery Tests ---

    def test_gallery_direct_file_upload(self):
        """Test creating gallery item via direct image upload."""
        payload = {
            "caption": "Direct Gallery Caption",
            "order": 1,
            "image": self.valid_image,
        }
        response = self.client.post(self.gallery_url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data["image"]["id"])

    def test_gallery_media_id(self):
        """Test creating gallery item via existing Media ID."""
        media = MediaFactory()
        payload = {
            "caption": "ID Gallery Caption",
            "order": 2,
            "image_id": media.id,
        }
        response = self.client.post(self.gallery_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["image"]["id"], media.id)

    # --- Categories Tests ---

    def test_category_direct_icon_upload(self):
        """Test creating category with direct icon file upload."""
        payload = {
            "name": "Direct Icon Cat",
            "slug": "direct-icon-cat",
            "icon": self.valid_image,
        }
        response = self.client.post(self.categories_url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data["icon"]["id"])

    def test_category_icon_media_id(self):
        """Test creating category using icon_id."""
        media = MediaFactory()
        payload = {
            "name": "ID Icon Cat",
            "slug": "id-icon-cat",
            "icon_id": media.id,
        }
        response = self.client.post(self.categories_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["icon"]["id"], media.id)

    # --- Podcast Categories Tests ---

    def test_podcast_category_direct_icon_upload(self):
        """Test creating podcast category with direct icon upload."""
        payload = {
            "title": "Direct Pod Cat",
            "slug": "direct-pod-cat",
            "icon": self.valid_image,
        }
        response = self.client.post(self.podcast_categories_url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data["icon"]["id"])

    def test_podcast_category_icon_media_id(self):
        """Test creating podcast category using icon_id."""
        media = MediaFactory()
        payload = {
            "title": "ID Pod Cat",
            "slug": "id-pod-cat",
            "icon_id": media.id,
        }
        response = self.client.post(self.podcast_categories_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["icon"]["id"], media.id)

    # --- Author Profiles Tests ---

    def test_author_profile_avatar_upload(self):
        """Test updating author profile avatar via direct file upload and media ID."""
        author = AuthorProfileFactory()
        detail_url = reverse("posts:authorprofile-detail", kwargs={"pk": author.pk})

        # 1. Direct upload
        response = self.client.patch(detail_url, {"avatar": self.valid_image}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data["avatar"]["id"])

        # 2. Existing Media ID
        media = MediaFactory()
        response = self.client.patch(detail_url, {"avatar_id": media.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["avatar"]["id"], media.id)
