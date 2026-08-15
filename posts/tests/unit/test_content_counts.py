from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from medias.models import Media
from posts.models import (
    Article,
    AuthorProfile,
    GalleryItem,
    Podcast,
    PodcastCategory,
)
from users.models import User


class ContentCountsAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="author", password="password")
        self.author_profile = AuthorProfile.objects.create(
            user=self.user, display_name="Author"
        )
        self.podcast_cat = PodcastCategory.objects.create(title="Tech", slug="tech-cat")

        # Create published and draft articles
        Article.objects.create(
            author=self.author_profile,
            status="published",
            published_at=timezone.now() - timedelta(days=1),
        )
        Article.objects.create(
            author=self.author_profile,
            status="published",
            published_at=timezone.now() - timedelta(hours=2),
        )
        Article.objects.create(
            author=self.author_profile,
            status="draft",
        )

        # Create podcasts
        Podcast.objects.create(
            title="Podcast 1",
            slug="podcast-1",
            category=self.podcast_cat,
            episode_number=1,
            duration=30,
            published_date=timezone.now(),
            is_active=True,
        )
        Podcast.objects.create(
            title="Podcast 2",
            slug="podcast-2",
            category=self.podcast_cat,
            episode_number=2,
            duration=45,
            published_date=timezone.now(),
            is_active=False,
        )

        # Create media images
        Media.objects.create(
            storage_key="test1.jpg",
            url="http://example.com/test1.jpg",
            type="image",
            mime="image/jpeg",
            uploaded_by=self.user,
        )
        Media.objects.create(
            storage_key="test2.png",
            url="http://example.com/test2.png",
            type="image",
            mime="image/png",
            uploaded_by=self.user,
            is_deleted=True,
        )

        # Create GalleryItem
        GalleryItem.objects.create(caption="Gallery 1", is_active=True)

    def test_content_counts_endpoints(self):
        urls = [
            reverse("posts:content-counts"),
            reverse("posts:content-counts-alias"),
            reverse("posts:article-counts-alias"),
        ]

        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.data["data"] if "data" in response.data else response.data

            self.assertEqual(data["articles_count"], 2)
            self.assertEqual(data["articles"], 2)

            self.assertEqual(data["podcasts_count"], 1)
            self.assertEqual(data["podcasts"], 1)

            self.assertEqual(data["images_count"], 1)
            self.assertEqual(data["images"], 1)

            self.assertEqual(data["gallery_count"], 1)
