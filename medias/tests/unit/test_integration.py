import json
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from medias.models import Media, ArticleMedia
from posts.factories import UserFactory
from posts.models import Article, ArticleTranslation, AuthorProfile


class MediaIntegrationTests(APITestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
        # Create AuthorProfile for the user
        self.author = AuthorProfile.objects.create(
            user=self.user,
            display_name="Architect Admin"
        )

    def test_safe_media_deletion_and_override(self):
        # Create media
        jpeg_data = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00_test..."
        file_obj = SimpleUploadedFile("delete_test.jpg", jpeg_data, content_type="image/jpeg")
        response = self.client.post(
            reverse("medias:media-list"),
            {"file": file_obj, "title": "Delete Test"},
            format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        media_id = response.data["id"]
        media = Media.objects.get(pk=media_id)

        # Link media to an article
        article = Article.objects.create(
            author=self.author,
            cover_image=media
        )

        # Try to delete media without force
        delete_url = reverse("medias:media-detail", kwargs={"pk": media_id})
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "MEDIA_IN_USE")

        # Delete with force override
        response = self.client.delete(f"{delete_url}?force=true")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        media.refresh_from_db()
        self.assertTrue(media.is_deleted)

    def test_search_and_filtering_api(self):
        # Create different media items
        jpeg_data = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00..."
        file1 = SimpleUploadedFile("arch.jpg", jpeg_data, content_type="image/jpeg")
        file2 = SimpleUploadedFile("nature.jpg", jpeg_data, content_type="image/jpeg")

        # Upload arch
        self.client.post(
            reverse("medias:media-list"),
            {"file": file1, "title": "Architecture design"},
            format="multipart"
        )
        # Upload nature
        self.client.post(
            reverse("medias:media-list"),
            {"file": file2, "title": "Beautiful Nature"},
            format="multipart"
        )

        # 1. Search title containing 'arch'
        response = self.client.get(reverse("medias:media-list") + "?q=arch")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["data"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Architecture design")

        # Check expanded detail serialization contains metadata and variants
        self.assertIn("metadata", results[0])
        self.assertIn("variants", results[0])

    def test_article_first_inline_block_uploads(self):
        # Prepare content blocks with "file" indicating inline upload
        content_blocks = [
            {
                "id": "block-img-1",
                "type": "image",
                "version": 1,
                "order": 1,
                "file": "inline_image.jpg",
                "data": {
                    "caption": "Sunset scene"
                }
            }
        ]

        # Create a file matching "inline_image.jpg"
        jpeg_data = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00_inline..."
        uploaded_file = SimpleUploadedFile("inline_image.jpg", jpeg_data, content_type="image/jpeg")

        # Post to article creation endpoint
        payload = {
            "title": "New Article",
            "excerpt": "This is an excerpt",
            "content_blocks": json.dumps(content_blocks),
            "inline_image.jpg": uploaded_file,
            "language_code": "en"
        }

        response = self.client.post(
            reverse("posts:article-list"),
            payload,
            format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check that the article was created with media reference set in the block data!
        article_id = response.data["id"]
        article = Article.objects.get(pk=article_id)
        trans = ArticleTranslation.objects.get(article=article, language_code="en")

        updated_blocks = trans.content_blocks
        self.assertEqual(len(updated_blocks), 1)
        self.assertIn("media_id", updated_blocks[0]["data"])
        self.assertNotIn("file", updated_blocks[0])
