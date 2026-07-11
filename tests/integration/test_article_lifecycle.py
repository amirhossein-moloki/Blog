from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from medias.models import ArticleMedia
from posts.blog_tests.base import BaseAPITestCase
from posts.factories import MediaFactory, ArticleFactory
from posts.models import Article
from posts.services import publish_scheduled_articles


class ArticleLifecycleIntegrationTest(BaseAPITestCase):
    def test_article_creation_and_media_sync(self):
        self._authenticate_as_staff()
        media = MediaFactory(storage_key="test-image.avif")

        url = reverse("posts:article-list")
        article_data = {
            "title": "Article with Media",
            "slug": "article-with-media",
            "excerpt": "Excerpt",
            "content": f'<p>Check this out: <img src="/media/{media.storage_key}" /></p>',
            "status": "published",
            "author": self.staff_author_profile.pk,
        }

        response = self.client.post(url, article_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        article = Article.objects.get(translations__slug="article-with-media")

        # Verify sync_article_media associated the media
        attachments = ArticleMedia.objects.filter(
            article=article, media=media, attachment_type="in-content"
        )
        self.assertTrue(attachments.exists())

    def test_scheduled_article_publishing(self):
        # Create a scheduled article set for the past
        past_time = timezone.now() - timedelta(minutes=10)
        article = ArticleFactory(
            status="scheduled", scheduled_at=past_time, published_at=None
        )

        # Ensure it is currently scheduled
        self.assertEqual(article.status, "scheduled")

        # Trigger the publishing service (usually called by Celery)
        publish_scheduled_articles()

        article.refresh_from_db()
        self.assertEqual(article.status, "published")
        self.assertIsNotNone(article.published_at)
        self.assertIsNone(article.scheduled_at)

    def test_article_creation_with_cover_and_og_image(self):
        self._authenticate_as_staff()
        cover = MediaFactory(storage_key="cover.jpg")
        og_image = MediaFactory(storage_key="og.jpg")

        url = reverse("posts:article-list")
        article_data = {
            "title": "Article with Cover",
            "slug": "article-with-cover",
            "excerpt": "Excerpt",
            "content": "Content",
            "cover_image_id": cover.pk,
            "og_image_id": og_image.pk,
            "author": self.staff_author_profile.pk,
        }

        response = self.client.post(url, article_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        article = Article.objects.get(translations__slug="article-with-cover")
        self.assertEqual(article.cover_image, cover)
        self.assertEqual(article.og_image, og_image)

        # Verify ArticleMedia attachments for cover and og-image
        self.assertTrue(
            ArticleMedia.objects.filter(
                article=article, media=cover, attachment_type="cover"
            ).exists()
        )
        self.assertTrue(
            ArticleMedia.objects.filter(
                article=article, media=og_image, attachment_type="og-image"
            ).exists()
        )
