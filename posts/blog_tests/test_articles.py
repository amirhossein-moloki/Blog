from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from posts.blog_tests.base import BaseAPITestCase
from posts.factories import (
    CategoryFactory,
    MediaFactory,
    ArticleFactory,
    SeriesFactory,
    TagFactory,
    UserFactory,
)
from posts.models import AuthorProfile, Article


class ArticlePermissionAPITest(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("posts:article-list")
        self.article_data = {
            "title": "Test Article by Author",
            "slug": "test-article-by-author",
            "excerpt": "An excerpt.",
            "content": "Some content.",
        }

    def test_guest_user_can_list_articles(self):
        ArticleFactory.create_batch(3)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 3)

    def test_guest_user_cannot_create_article(self):
        response = self.client.post(self.url, self.article_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_without_author_profile_cannot_create_article(self):
        # Create a new user that doesn't have an author profile
        regular_user = UserFactory()
        AuthorProfile.objects.filter(
            user=regular_user
        ).delete()  # Ensure no profile exists
        self._authenticate(regular_user)
        response = self.client.post(self.url, self.article_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_author_user_can_create_article(self):
        # self.user from BaseAPITestCase needs an author profile explicitly created
        AuthorProfile.objects.get_or_create(
            user=self.user, display_name=self.user.username
        )
        self._authenticate(self.user)
        response = self.client.post(self.url, self.article_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Article.objects.filter(translations__slug=self.article_data["slug"]).exists()
        )

    def test_staff_user_can_create_article(self):
        self._authenticate_as_staff()
        article_data = self.article_data.copy()
        article_data["title"] = "Test Article by Staff"
        article_data["slug"] = "test-article-by-staff"
        response = self.client.post(self.url, article_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Article.objects.filter(translations__slug=article_data["slug"]).exists()
        )


class ArticleAPITest(BaseAPITestCase):
    def test_create_article(self):
        self._authenticate_as_staff()
        category = CategoryFactory()
        tags = TagFactory.create_batch(2)
        url = reverse("posts:article-list")
        data = {
            "title": "New Article",
            "slug": "new-article",
            "excerpt": "An excerpt.",
            "content": "Some content.",
            "status": "draft",
            "visibility": "private",
            "author": self.staff_author_profile.pk,
            "category": category.pk,
            "tag_ids": [tag.pk for tag in tags],
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Article.objects.filter(translations__slug="new-article").exists())
        new_article = Article.objects.get(translations__slug="new-article")
        self.assertEqual(new_article.tags.count(), 2)
        self.assertIsNotNone(new_article.translation.reading_time_sec)

    def test_list_articles(self):
        ArticleFactory.create_batch(3)
        url = reverse("posts:article-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 3)

    def test_default_ordering_is_latest_first(self):
        older_article = ArticleFactory(published_at=timezone.now() - timedelta(days=3))
        newest_article = ArticleFactory(published_at=timezone.now())
        middle_article = ArticleFactory(published_at=timezone.now() - timedelta(days=1))

        url = reverse("posts:article-list")
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = [article["id"] for article in response.data["data"]]
        self.assertEqual(
            returned_ids[:3], [newest_article.id, middle_article.id, older_article.id]
        )

    def test_article_pagination(self):
        ArticleFactory.create_batch(15)
        url = reverse("posts:article-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 10)
        self.assertIn("pagination", response.data)
        self.assertIsNotNone(response.data["pagination"])

    def test_article_filtering(self):
        series = SeriesFactory()
        category = CategoryFactory()
        tag1 = TagFactory()
        tag2 = TagFactory()

        ArticleFactory(series=series, visibility="private", category=category, tags=[tag1])
        ArticleFactory.create_batch(2, visibility="public", tags=[tag2])
        url = reverse("posts:article-list")

        # Filter by series
        response = self.client.get(url, {"series": series.pk}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)

        # Filter by visibility
        response = self.client.get(url, {"visibility": "public"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)

        # Filter by category
        response = self.client.get(url, {"category": category.slug}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)

        # Filter by tags
        response = self.client.get(url, {"tags": tag1.slug}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)

        response = self.client.get(url, {"tags": tag2.slug}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)

    def test_article_is_hot_filtering(self):
        # Hot article: recent, high views
        ArticleFactory(published_at=timezone.now() - timedelta(days=15), views_count=2000)
        # Not hot article: old
        ArticleFactory(published_at=timezone.now() - timedelta(days=45), views_count=2000)
        # Not hot article: low views
        ArticleFactory(published_at=timezone.now() - timedelta(days=15), views_count=500)
        url = reverse("posts:article-list")

        # Filter by is_hot=True
        response = self.client.get(url, {"is_hot": "true"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)

        # Filter by is_hot=False
        response = self.client.get(url, {"is_hot": "false"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)

    def test_article_date_filtering(self):
        ArticleFactory(published_at=timezone.now() - timedelta(days=5))
        ArticleFactory(published_at=timezone.now() - timedelta(days=15))
        url = reverse("posts:article-list")

        # Filter by published_after
        after_date = (timezone.now() - timedelta(days=10)).isoformat()
        response = self.client.get(url, {"published_after": after_date}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)

    def test_slug_endpoint_returns_id_and_author_avatar(self):
        author_profile = self.author_profile
        author_profile.avatar = MediaFactory()
        author_profile.save()

        article = ArticleFactory(status="published", author=author_profile)

        url = reverse("posts:article-by-slug", kwargs={"slug": article.translation.slug})
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], article.id)
        self.assertIn("author", response.data)
        self.assertEqual(
            response.data["author"]["display_name"], author_profile.display_name
        )
        self.assertIsNotNone(response.data["author"]["avatar"])

    def test_retrieve_article(self):
        yesterday = timezone.now() - timedelta(days=1)
        cover_image = MediaFactory()
        in_content_media = MediaFactory()

        content = f'<p>Some text</p><img src="/media/{in_content_media.storage_key}" />'
        article = ArticleFactory(
            status="published",
            published_at=yesterday,
            cover_image=cover_image,
            translation__content=content,
        )
        article.translation.save()  # Trigger the media attachment logic

        url = reverse("posts:article-detail", kwargs={"slug": article.translation.slug})
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], article.translation.title)

        # Check for media attachments
        self.assertIn("media_attachments", response.data)
        attachments = response.data["media_attachments"]
        self.assertEqual(len(attachments), 2)

        attachment_types = {att["attachment_type"] for att in attachments}
        self.assertIn("cover", attachment_types)
        self.assertIn("in-content", attachment_types)

    def test_update_article(self):
        self._authenticate_as_staff()
        article = ArticleFactory(author=self.staff_author_profile)
        url = reverse("posts:article-detail", kwargs={"slug": article.translation.slug})
        data = {"title": "Updated Title"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        article.refresh_from_db()
        self.assertEqual(article.translation.title, "Updated Title")

    def test_admin_can_update_other_users_article(self):
        """
        Ensures an admin can update an article they do not own.
        """
        self._authenticate_as_staff()
        # self.user is the non-staff user, self.author_profile is their profile
        article = ArticleFactory(author=self.author_profile)
        url = reverse("posts:article-detail", kwargs={"slug": article.translation.slug})
        data = {"title": "Admin Edited Title"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        article.refresh_from_db()
        self.assertEqual(article.translation.title, "Admin Edited Title")

    def test_delete_article(self):
        self._authenticate_as_staff()
        article = ArticleFactory(author=self.staff_author_profile)
        url = reverse("posts:article-detail", kwargs={"slug": article.translation.slug})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Article.objects.filter(pk=article.pk).exists())

    def test_related_articles_pagination(self):
        tag = TagFactory()
        article = ArticleFactory(tags=[tag])
        ArticleFactory.create_batch(15, tags=[tag])
        url = reverse("posts:article-related", kwargs={"slug": article.translation.slug})
        response = self.client.get(url, {"page_size": 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 5)
        self.assertIn("pagination", response.data)

    def test_same_category_articles_pagination(self):
        category = CategoryFactory()
        article = ArticleFactory(category=category)
        ArticleFactory.create_batch(15, category=category)
        url = reverse(
            "posts:article-same-category", kwargs={"slug": article.translation.slug}
        )
        response = self.client.get(url, {"page_size": 7})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 7)
        self.assertIn("pagination", response.data)
