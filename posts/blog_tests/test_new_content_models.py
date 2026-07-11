from django.urls import reverse
from rest_framework import status
from posts.blog_tests.base import BaseAPITestCase
from posts.factories import (
    CategoryFactory,
    PostFactory,
    PodcastCategoryFactory,
    PodcastFactory,
    GalleryItemFactory,
)
from posts.models import Category, Post, PodcastCategory, Podcast, GalleryItem, PostTranslation


class NewContentModelsAPITest(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        # URLs
        self.podcast_cat_list_url = reverse("posts:podcastcategory-list")
        self.podcast_list_url = reverse("posts:podcast-list")
        self.gallery_list_url = reverse("posts:galleryitem-list")

    def test_category_icon_field(self):
        """Test Category icon and serialization."""
        self._authenticate_as_staff()
        category = CategoryFactory()
        url = reverse("posts:category-detail", kwargs={"pk": category.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("icon", response.data)

    def test_post_related_posts_and_short_description(self):
        """Test Post related_posts and short_description field."""
        self._authenticate_as_staff()
        post1 = PostFactory()
        post2 = PostFactory()

        # Test short_description write-only/read-only flow
        payload = {
            "title": "New Post with short desc",
            "slug": "new-post-with-short-desc",
            "excerpt": "My excerpt",
            "short_description": "My short description text for SEO card.",
            "content": "<p>Content with rich text</p>",
            "related_post_ids": [post1.pk, post2.pk]
        }

        response = self.client.post(reverse("posts:post-list"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        post_id = response.data["id"]

        # Retrieve detailed post to check short_description and related_posts
        detail_url = reverse("posts:post-detail", kwargs={"slug": "new-post-with-short-desc"})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["short_description"], "My short description text for SEO card.")
        self.assertEqual(len(response.data["related_posts"]), 2)

    def test_podcast_category_api(self):
        """Test PodcastCategory API endpoints."""
        # Unauthenticated listing is fine
        PodcastCategoryFactory.create_batch(2)
        response = self.client.get(self.podcast_cat_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        # Authenticated (as staff) create
        self._authenticate_as_staff()
        payload = {
            "title": "New Pod Cat",
            "slug": "new-pod-cat"
        }
        response = self.client.post(self.podcast_cat_list_url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(PodcastCategory.objects.filter(slug="new-pod-cat").exists())

    def test_podcast_api(self):
        """Test Podcast API endpoints including retrieval view_count increment."""
        category = PodcastCategoryFactory()
        podcast = PodcastFactory(category=category, title="Initial Pod Title", slug="initial-pod")

        # Guest user retrieve
        detail_url = reverse("posts:podcast-detail", kwargs={"slug": "initial-pod"})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["view_count"], 1) # incremented on retrieve

        # Test listing
        response = self.client.get(self.podcast_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        # Authenticated as staff can create
        self._authenticate_as_staff()
        payload = {
            "title": "New Episode Title",
            "slug": "new-episode",
            "category": category.pk,
            "episode_number": 12,
            "cover_image": podcast.cover_image,  # Re-use cover file
            "media_type": "audio",
            "description": "<p>A detailed podcast episode description with bullet points.</p>",
            "duration": 30,
            "published_date": "2026-07-11T12:00:00Z"
        }
        response = self.client.post(self.podcast_list_url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Podcast.objects.filter(slug="new-episode").exists())

    def test_gallery_item_api(self):
        """Test GalleryItem API endpoints."""
        # Listing
        GalleryItemFactory.create_batch(3)
        response = self.client.get(self.gallery_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

        # Authenticated create
        self._authenticate_as_staff()
        item = GalleryItemFactory()
        payload = {
            "caption": "Beautiful Polaroid Caption",
            "order": 5,
            "image": item.image,
            "link": "https://example.com/some-article"
        }
        response = self.client.post(self.gallery_list_url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(GalleryItem.objects.filter(caption="Beautiful Polaroid Caption").exists())
