from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from medias.models import ArticleMedia, Media
from posts.factories import ArticleFactory
from posts.models import Article
from posts.services import (
    increment_article_view_count,
    publish_scheduled_articles,
    sync_article_media,
)


class ArticleServiceTests(TestCase):
    def test_increment_article_view_count(self):
        article = ArticleFactory(views_count=5)
        increment_article_view_count(article.pk)
        article.refresh_from_db()
        self.assertEqual(article.views_count, 6)

    def test_increment_article_view_count_error(self):
        # Article.objects.filter(pk=article_id).update(...) doesn't raise error if not found,
        # but the service might have other error paths.
        with self.assertLogs("posts.services", level="ERROR") as cm:
            with patch(
                "posts.models.Article.objects.filter", side_effect=Exception("DB Error")
            ):
                increment_article_view_count(1)
                self.assertIn("Error incrementing view count", cm.output[0])

    def test_publish_scheduled_articles_no_articles(self):
        Article.objects.all().delete()
        with self.assertLogs("posts.services", level="INFO") as cm:
            publish_scheduled_articles()
            self.assertIn("No scheduled articles to publish", cm.output[0])

    def test_publish_scheduled_articles(self):
        now = timezone.now()
        past = now - timedelta(hours=1)
        future = now + timedelta(hours=1)

        p1 = ArticleFactory(status="scheduled", scheduled_at=past)
        p2 = ArticleFactory(status="scheduled", scheduled_at=future)
        p3 = ArticleFactory(status="draft")

        publish_scheduled_articles()

        p1.refresh_from_db()
        p2.refresh_from_db()
        p3.refresh_from_db()

        self.assertEqual(p1.status, "published")
        self.assertEqual(p1.published_at, past)
        self.assertIsNone(p1.scheduled_at)

        self.assertEqual(p2.status, "scheduled")
        self.assertEqual(p3.status, "draft")

    def test_sync_article_media_cover_and_og(self):
        article = ArticleFactory()
        media_cover = Media.objects.create(
            storage_key="cover.jpg",
            url="http://ex.com/cover.jpg",
            type="image",
            mime="image/jpeg",
        )
        media_og = Media.objects.create(
            storage_key="og.jpg",
            url="http://ex.com/og.jpg",
            type="image",
            mime="image/jpeg",
        )

        article.cover_image = media_cover
        article.og_image = media_og
        sync_article_media(article)

        self.assertTrue(
            ArticleMedia.objects.filter(
                article=article, media=media_cover, attachment_type="cover"
            ).exists()
        )
        self.assertTrue(
            ArticleMedia.objects.filter(
                article=article, media=media_og, attachment_type="og-image"
            ).exists()
        )

        # Remove them
        article.cover_image = None
        article.og_image = None
        sync_article_media(article)
        self.assertFalse(
            ArticleMedia.objects.filter(
                article=article, media=media_cover, attachment_type="cover"
            ).exists()
        )
        self.assertFalse(
            ArticleMedia.objects.filter(
                article=article, media=media_og, attachment_type="og-image"
            ).exists()
        )

    def test_sync_article_media_in_content(self):
        with self.settings(MEDIA_URL="/media/"):
            media = Media.objects.create(
                storage_key="content.jpg",
                url="/media/content.jpg",
                type="image",
                mime="image/jpeg",
            )
            article = ArticleFactory(
                translation__content='<img src="/media/content.jpg">'
            )
            # Article.save calls sync_article_media

            self.assertTrue(
                ArticleMedia.objects.filter(
                    article=article, media=media, attachment_type="in-content"
                ).exists()
            )

            # Change content
            trans = article.translation
            trans.content = "no image"
            sync_article_media(trans)
            self.assertFalse(
                ArticleMedia.objects.filter(
                    article=article, media=media, attachment_type="in-content"
                ).exists()
            )
