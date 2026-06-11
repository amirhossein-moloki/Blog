from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from medias.models import PostMedia
from posts.blog_tests.base import BaseAPITestCase
from posts.factories import MediaFactory, PostFactory
from posts.models import Post
from posts.services import publish_scheduled_posts


class PostLifecycleIntegrationTest(BaseAPITestCase):
    def test_post_creation_and_media_sync(self):
        self._authenticate_as_staff()
        media = MediaFactory(storage_key="test-image.avif")

        url = reverse("posts:post-list")
        post_data = {
            "title": "Post with Media",
            "slug": "post-with-media",
            "excerpt": "Excerpt",
            "content": f'<p>Check this out: <img src="/media/{media.storage_key}" /></p>',
            "status": "published",
            "author": self.staff_author_profile.pk,
        }

        response = self.client.post(url, post_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        post = Post.objects.get(slug="post-with-media")

        # Verify sync_post_media associated the media
        attachments = PostMedia.objects.filter(
            post=post, media=media, attachment_type="in-content"
        )
        self.assertTrue(attachments.exists())

    def test_scheduled_post_publishing(self):
        # Create a scheduled post set for the past
        past_time = timezone.now() - timedelta(minutes=10)
        post = PostFactory(
            status="scheduled", scheduled_at=past_time, published_at=None
        )

        # Ensure it is currently scheduled
        self.assertEqual(post.status, "scheduled")

        # Trigger the publishing service (usually called by Celery)
        publish_scheduled_posts()

        post.refresh_from_db()
        self.assertEqual(post.status, "published")
        self.assertIsNotNone(post.published_at)
        self.assertIsNone(post.scheduled_at)

    def test_post_creation_with_cover_and_og_image(self):
        self._authenticate_as_staff()
        cover = MediaFactory(storage_key="cover.jpg")
        og_image = MediaFactory(storage_key="og.jpg")

        url = reverse("posts:post-list")
        post_data = {
            "title": "Post with Cover",
            "slug": "post-with-cover",
            "excerpt": "Excerpt",
            "content": "Content",
            "cover_media_id": cover.pk,
            "og_image_id": og_image.pk,
            "author": self.staff_author_profile.pk,
        }

        response = self.client.post(url, post_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        post = Post.objects.get(slug="post-with-cover")
        self.assertEqual(post.cover_media, cover)
        self.assertEqual(post.og_image, og_image)

        # Verify PostMedia attachments for cover and og-image
        self.assertTrue(
            PostMedia.objects.filter(
                post=post, media=cover, attachment_type="cover"
            ).exists()
        )
        self.assertTrue(
            PostMedia.objects.filter(
                post=post, media=og_image, attachment_type="og-image"
            ).exists()
        )
