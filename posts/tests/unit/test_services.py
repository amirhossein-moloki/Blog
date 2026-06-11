from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from medias.models import Media, PostMedia
from posts.factories import PostFactory
from posts.models import Post
from posts.services import (
    increment_post_view_count,
    publish_scheduled_posts,
    sync_post_media,
)


class PostServiceTests(TestCase):
    def test_increment_post_view_count(self):
        post = PostFactory(views_count=5)
        increment_post_view_count(post.pk)
        post.refresh_from_db()
        self.assertEqual(post.views_count, 6)

    def test_increment_post_view_count_error(self):
        # Post.objects.filter(pk=post_id).update(...) doesn't raise error if not found,
        # but the service might have other error paths.
        with self.assertLogs("posts.services", level="ERROR") as cm:
            with patch(
                "posts.models.Post.objects.filter", side_effect=Exception("DB Error")
            ):
                increment_post_view_count(1)
                self.assertIn("Error incrementing view count", cm.output[0])

    def test_publish_scheduled_posts_no_posts(self):
        Post.objects.all().delete()
        with self.assertLogs("posts.services", level="INFO") as cm:
            publish_scheduled_posts()
            self.assertIn("No scheduled posts to publish", cm.output[0])

    def test_publish_scheduled_posts(self):
        now = timezone.now()
        past = now - timedelta(hours=1)
        future = now + timedelta(hours=1)

        p1 = PostFactory(status="scheduled", scheduled_at=past)
        p2 = PostFactory(status="scheduled", scheduled_at=future)
        p3 = PostFactory(status="draft")

        publish_scheduled_posts()

        p1.refresh_from_db()
        p2.refresh_from_db()
        p3.refresh_from_db()

        self.assertEqual(p1.status, "published")
        self.assertEqual(p1.published_at, past)
        self.assertIsNone(p1.scheduled_at)

        self.assertEqual(p2.status, "scheduled")
        self.assertEqual(p3.status, "draft")

    def test_sync_post_media_cover_and_og(self):
        post = PostFactory()
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

        post.cover_media = media_cover
        post.og_image = media_og
        sync_post_media(post)

        self.assertTrue(
            PostMedia.objects.filter(
                post=post, media=media_cover, attachment_type="cover"
            ).exists()
        )
        self.assertTrue(
            PostMedia.objects.filter(
                post=post, media=media_og, attachment_type="og-image"
            ).exists()
        )

        # Remove them
        post.cover_media = None
        post.og_image = None
        sync_post_media(post)
        self.assertFalse(
            PostMedia.objects.filter(
                post=post, media=media_cover, attachment_type="cover"
            ).exists()
        )
        self.assertFalse(
            PostMedia.objects.filter(
                post=post, media=media_og, attachment_type="og-image"
            ).exists()
        )

    def test_sync_post_media_in_content(self):
        with self.settings(MEDIA_URL="/media/"):
            media = Media.objects.create(
                storage_key="content.jpg",
                url="/media/content.jpg",
                type="image",
                mime="image/jpeg",
            )
            post = PostFactory(content='<img src="/media/content.jpg">')
            # Post.save calls sync_post_media

            self.assertTrue(
                PostMedia.objects.filter(
                    post=post, media=media, attachment_type="in-content"
                ).exists()
            )

            # Change content
            post.content = "no image"
            sync_post_media(post)
            self.assertFalse(
                PostMedia.objects.filter(
                    post=post, media=media, attachment_type="in-content"
                ).exists()
            )
