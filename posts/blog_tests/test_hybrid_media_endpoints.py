import os
import shutil
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from medias.models import Media
from posts.factories import (
    PodcastCategoryFactory,
    UserFactory,
)
from posts.models import (
    AuthorProfile,
    Category,
    GalleryItem,
    Podcast,
    PodcastCategory,
)

User = get_user_model()
TEST_MEDIA_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "test_hybrid_media"
)


@override_settings(MEDIA_ROOT=TEST_MEDIA_DIR)
class HybridMediaEndpointsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory(is_staff=True)
        self.client.force_authenticate(user=self.user)

        if os.path.exists(TEST_MEDIA_DIR):
            shutil.rmtree(TEST_MEDIA_DIR)
        os.makedirs(TEST_MEDIA_DIR)

    def tearDown(self):
        if os.path.exists(TEST_MEDIA_DIR):
            shutil.rmtree(TEST_MEDIA_DIR)

    def _create_dummy_image(self, name="image.jpg"):
        image_io = BytesIO()
        image = Image.new("RGB", (100, 100), color="blue")
        image.save(image_io, "jpeg")
        image_io.seek(0)
        return SimpleUploadedFile(name, image_io.getvalue(), content_type="image/jpeg")

    def _create_dummy_audio(self, name="audio.mp3"):
        return SimpleUploadedFile(
            name, b"ID3v2fakeaudiobytes", content_type="audio/mpeg"
        )

    def _create_media(self, filename="existing.jpg", mime="image/jpeg"):
        SimpleUploadedFile(filename, b"\x00" * 100, content_type=mime)
        return Media.objects.create(
            storage_key=f"uploads/{filename}",
            url=f"/media/uploads/{filename}",
            mime=mime,
            type="image" if "image" in mime else "file",
            size_bytes=100,
            uploaded_by=self.user,
            title=filename,
        )

    # -------------------------------------------------------------------------
    # Podcasts Endpoint Tests
    # -------------------------------------------------------------------------
    def test_podcast_direct_file_upload(self):
        """Test creating podcast with direct file uploads for cover_image and audio_file."""
        category = PodcastCategoryFactory()
        cover_file = self._create_dummy_image("pod_cover.jpg")
        audio_file = self._create_dummy_audio("pod_audio.mp3")

        url = reverse("posts:podcast-list")
        payload = {
            "title": "Direct Upload Podcast",
            "slug": "direct-upload-podcast",
            "category": category.pk,
            "episode_number": 1,
            "cover_image": cover_file,
            "audio_file": audio_file,
            "media_type": "audio",
            "duration": 30,
            "published_date": "2026-08-16T10:00:00Z",
        }

        response = self.client.post(url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        podcast = Podcast.objects.get(slug="direct-upload-podcast")
        self.assertIsNotNone(podcast.cover_image)
        self.assertIsNotNone(podcast.audio_file)
        self.assertIn("cover_image", response.data)
        self.assertIsNotNone(response.data["cover_image"])
        self.assertEqual(response.data["cover_image"]["id"], podcast.cover_image.id)

    def test_podcast_media_id_assignment(self):
        """Test creating podcast referencing existing Media IDs."""
        category = PodcastCategoryFactory()
        cover_media = self._create_media("cover.jpg")
        audio_media = self._create_media("audio.mp3", mime="audio/mpeg")

        url = reverse("posts:podcast-list")
        payload = {
            "title": "Media ID Podcast",
            "slug": "media-id-podcast",
            "category": category.pk,
            "episode_number": 2,
            "cover_image_id": cover_media.id,
            "audio_file_id": audio_media.id,
            "media_type": "audio",
            "duration": 40,
            "published_date": "2026-08-16T11:00:00Z",
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        podcast = Podcast.objects.get(slug="media-id-podcast")
        self.assertEqual(podcast.cover_image, cover_media)
        self.assertEqual(podcast.audio_file, audio_media)

    def test_podcast_simultaneous_id_and_file_error(self):
        """Test error when both ID and direct file are provided for podcast cover_image."""
        category = PodcastCategoryFactory()
        cover_media = self._create_media("cover.jpg")
        cover_file = self._create_dummy_image("cover_file.jpg")

        url = reverse("posts:podcast-list")
        payload = {
            "title": "Conflicting Podcast",
            "slug": "conflicting-podcast",
            "category": category.pk,
            "episode_number": 3,
            "cover_image": cover_file,
            "cover_image_id": cover_media.id,
            "media_type": "audio",
            "duration": 20,
            "published_date": "2026-08-16T12:00:00Z",
        }

        response = self.client.post(url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cover_image", str(response.data))

    def test_podcast_invalid_media_id(self):
        """Test error when non-existent media_id is provided."""
        category = PodcastCategoryFactory()
        url = reverse("posts:podcast-list")
        payload = {
            "title": "Invalid Media Podcast",
            "slug": "invalid-media-podcast",
            "category": category.pk,
            "episode_number": 4,
            "cover_image_id": 999999,
            "media_type": "audio",
            "duration": 15,
            "published_date": "2026-08-16T13:00:00Z",
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -------------------------------------------------------------------------
    # Gallery Endpoint Tests
    # -------------------------------------------------------------------------
    def test_gallery_direct_file_upload(self):
        """Test gallery item creation with direct image file upload."""
        image_file = self._create_dummy_image("gallery.jpg")
        url = reverse("posts:galleryitem-list")
        payload = {
            "caption": "Direct Gallery Image",
            "order": 1,
            "image": image_file,
        }

        response = self.client.post(url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        item = GalleryItem.objects.get(caption="Direct Gallery Image")
        self.assertIsNotNone(item.image)
        self.assertIn("image", response.data)
        self.assertEqual(response.data["image"]["id"], item.image.id)

    def test_gallery_media_id_assignment(self):
        """Test gallery item creation with existing Media ID."""
        image_media = self._create_media("gallery_item.jpg")
        url = reverse("posts:galleryitem-list")
        payload = {
            "caption": "ID Gallery Image",
            "order": 2,
            "image_id": image_media.id,
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        item = GalleryItem.objects.get(caption="ID Gallery Image")
        self.assertEqual(item.image, image_media)

    def test_gallery_simultaneous_id_and_file_error(self):
        """Test error when both image and image_id are sent for gallery item."""
        image_media = self._create_media("gallery_item.jpg")
        image_file = self._create_dummy_image("upload.jpg")
        url = reverse("posts:galleryitem-list")
        payload = {
            "caption": "Conflict Gallery",
            "order": 3,
            "image": image_file,
            "image_id": image_media.id,
        }

        response = self.client.post(url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -------------------------------------------------------------------------
    # Categories Endpoint Tests
    # -------------------------------------------------------------------------
    def test_category_direct_file_upload(self):
        """Test category creation with direct icon file upload."""
        icon_file = self._create_dummy_image("cat_icon.jpg")
        url = reverse("posts:category-list")
        payload = {
            "name": "Direct Category",
            "slug": "direct-category",
            "icon": icon_file,
        }

        response = self.client.post(url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        category = Category.objects.get(slug="direct-category")
        self.assertIsNotNone(category.icon)
        self.assertEqual(response.data["icon"]["id"], category.icon.id)

    def test_category_media_id_assignment(self):
        """Test category creation with Media ID for icon."""
        icon_media = self._create_media("cat_icon_media.jpg")
        url = reverse("posts:category-list")
        payload = {
            "name": "ID Category",
            "slug": "id-category",
            "icon_id": icon_media.id,
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        category = Category.objects.get(slug="id-category")
        self.assertEqual(category.icon, icon_media)

    def test_category_simultaneous_id_and_file_error(self):
        """Test error when both icon and icon_id are provided."""
        icon_media = self._create_media("cat_icon_media.jpg")
        icon_file = self._create_dummy_image("cat_file.jpg")
        url = reverse("posts:category-list")
        payload = {
            "name": "Conflict Category",
            "slug": "conflict-category",
            "icon": icon_file,
            "icon_id": icon_media.id,
        }

        response = self.client.post(url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -------------------------------------------------------------------------
    # Podcast Categories Endpoint Tests
    # -------------------------------------------------------------------------
    def test_podcast_category_direct_file_upload(self):
        """Test podcast category creation with direct icon file upload."""
        icon_file = self._create_dummy_image("pod_cat_icon.jpg")
        url = reverse("posts:podcastcategory-list")
        payload = {
            "title": "Direct Pod Cat",
            "slug": "direct-pod-cat",
            "icon": icon_file,
        }

        response = self.client.post(url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        pod_cat = PodcastCategory.objects.get(slug="direct-pod-cat")
        self.assertIsNotNone(pod_cat.icon)
        self.assertEqual(response.data["icon"]["id"], pod_cat.icon.id)

    def test_podcast_category_media_id_assignment(self):
        """Test podcast category creation with icon_id."""
        icon_media = self._create_media("pod_cat_icon.jpg")
        url = reverse("posts:podcastcategory-list")
        payload = {
            "title": "ID Pod Cat",
            "slug": "id-pod-cat",
            "icon_id": icon_media.id,
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        pod_cat = PodcastCategory.objects.get(slug="id-pod-cat")
        self.assertEqual(pod_cat.icon, icon_media)

    def test_podcast_category_simultaneous_id_and_file_error(self):
        """Test error when both icon and icon_id are passed for podcast category."""
        icon_media = self._create_media("icon.jpg")
        icon_file = self._create_dummy_image("icon_file.jpg")
        url = reverse("posts:podcastcategory-list")
        payload = {
            "title": "Conflict Pod Cat",
            "slug": "conflict-pod-cat",
            "icon": icon_file,
            "icon_id": icon_media.id,
        }

        response = self.client.post(url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -------------------------------------------------------------------------
    # Author Profile Endpoint Tests
    # -------------------------------------------------------------------------
    def test_author_profile_direct_avatar_upload(self):
        """Test updating author profile with direct avatar file upload."""
        author_user = UserFactory()
        profile, _ = AuthorProfile.objects.get_or_create(
            user=author_user, defaults={"display_name": "Author Person"}
        )
        avatar_file = self._create_dummy_image("author_avatar.jpg")

        url = reverse("posts:authorprofile-detail", kwargs={"pk": profile.pk})
        payload = {
            "display_name": "Updated Author Person",
            "avatar": avatar_file,
        }

        response = self.client.patch(url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        profile.refresh_from_db()
        self.assertIsNotNone(profile.avatar)
        self.assertEqual(response.data["avatar"]["id"], profile.avatar.id)

    def test_author_profile_avatar_id_assignment(self):
        """Test updating author profile with existing avatar Media ID."""
        author_user = UserFactory()
        profile, _ = AuthorProfile.objects.get_or_create(
            user=author_user, defaults={"display_name": "Author Person"}
        )
        avatar_media = self._create_media("author_media.jpg")

        url = reverse("posts:authorprofile-detail", kwargs={"pk": profile.pk})
        payload = {
            "avatar_id": avatar_media.id,
        }

        response = self.client.patch(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        profile.refresh_from_db()
        self.assertEqual(profile.avatar, avatar_media)
