import os
import shutil
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from medias.models import Media

User = get_user_model()

TEST_MEDIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_media")


@override_settings(MEDIA_ROOT=TEST_MEDIA_DIR)
class MediaAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpassword", is_staff=True
        )
        self.client.force_authenticate(user=self.user)

        if os.path.exists(TEST_MEDIA_DIR):
            shutil.rmtree(TEST_MEDIA_DIR)
        os.makedirs(TEST_MEDIA_DIR)

    def tearDown(self):
        if os.path.exists(TEST_MEDIA_DIR):
            shutil.rmtree(TEST_MEDIA_DIR)

    def _create_dummy_image(self, name="test.jpg", content_type="image/jpeg"):
        image_io = BytesIO()
        image = Image.new("RGB", (100, 100), color="red")
        image.save(image_io, "jpeg")
        image_io.seek(0)
        return SimpleUploadedFile(name, image_io.getvalue(), content_type=content_type)

    def test_media_upload_no_optimization(self):
        """
        Tests that an uploaded image is correctly saved without AVIF conversion.
        """
        image_file = self._create_dummy_image(name="test_upload.jpg")

        # Upload the image via API
        response = self.client.post(
            reverse("medias:media-list"), {"file": image_file}, format="multipart"
        )

        # Assert successful creation and response structure
        self.assertEqual(
            response.status_code,
            201,
            f"API returned errors: {response.content.decode()}",
        )
        self.assertIn("id", response.data)
        self.assertIn("url", response.data)
        # Optimization removed, so should NOT end with .avif
        self.assertFalse(response.data["url"].endswith(".avif"))
        self.assertTrue(response.data["url"].endswith(".jpg"))

        # Assert database state
        self.assertEqual(Media.objects.count(), 1)
        media = Media.objects.first()
        self.assertTrue(media.storage_key.endswith(".jpg"))
        self.assertEqual(media.mime, "image/jpeg")
        self.assertEqual(media.type, "image")
        self.assertIsNotNone(media.width)
        self.assertIsNotNone(media.height)

        # Assert file existence
        self.assertTrue(default_storage.exists(media.storage_key))

    def test_article_create_with_direct_cover_and_og_upload(self):
        """
        Tests that an article can be created with cover_image_id and og_image_id
        uploaded directly as files in the same request.
        """
        from posts.models import Article, AuthorProfile

        AuthorProfile.objects.get_or_create(
            user=self.user, display_name=self.user.username
        )

        cover_file = self._create_dummy_image(name="my_cover.jpg")
        og_file = self._create_dummy_image(name="my_og.jpg")

        data = {
            "title": "Article with Uploaded Images",
            "slug": "article-uploaded-images",
            "excerpt": "Excerpt text",
            "content": "Some HTML content.",
            "cover_image_id": cover_file,
            "og_image_id": og_file,
        }

        response = self.client.post(
            reverse("posts:article-list"), data, format="multipart"
        )
        self.assertEqual(response.status_code, 201, response.data)

        article = Article.objects.get(translations__slug="article-uploaded-images")
        self.assertIsNotNone(article.cover_image)
        self.assertIsNotNone(article.og_image)
        self.assertEqual(article.cover_image.title, "my_cover.jpg")
        self.assertEqual(article.og_image.title, "my_og.jpg")

    def test_article_create_with_inline_media_upload(self):
        """
        Tests that inline images uploaded within the request are matched with <img> tags,
        uploaded, and substituted with real media URLs.
        """
        from posts.models import Article, AuthorProfile

        AuthorProfile.objects.get_or_create(
            user=self.user, display_name=self.user.username
        )

        inline_file = self._create_dummy_image(name="inline_image.jpg")
        content = (
            '<p>Check out this image:</p><img src="inline_image.jpg" alt="inline" />'
        )

        data = {
            "title": "Article with Inline Image",
            "slug": "article-inline-image",
            "excerpt": "Excerpt text",
            "content": content,
            "inline_file": inline_file,
        }

        response = self.client.post(
            reverse("posts:article-list"), data, format="multipart"
        )
        self.assertEqual(response.status_code, 201, response.data)

        article = Article.objects.get(translations__slug="article-inline-image")
        translation = article.translations.get(language_code="en")

        # Verify that the src in translation.content was updated
        self.assertNotIn('src="inline_image.jpg"', translation.content)
        self.assertIn("/media/inline_image", translation.content)

        # Verify that the media attachment was linked as in-content
        attachments = article.media_attachments.filter(attachment_type="in-content")
        self.assertEqual(attachments.count(), 1)
        self.assertEqual(attachments.first().media.title, "inline_image.jpg")
