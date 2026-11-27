from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from posts.blog_tests.base import BaseAPITestCase
from posts.factories import (
    ArticleFactory,
    CategoryFactory,
    MediaFactory,
    SeriesFactory,
    TagFactory,
    UserFactory,
)
from posts.models import Article, AuthorProfile


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
            Article.objects.filter(
                translations__slug=self.article_data["slug"]
            ).exists()
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
        self.assertTrue(
            Article.objects.filter(translations__slug="new-article").exists()
        )
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

        private_article = ArticleFactory(
            series=series, visibility="private", category=category, tags=[tag1]
        )
        unlisted_article = ArticleFactory(
            series=series, visibility="unlisted", category=category, tags=[tag1]
        )
        ArticleFactory.create_batch(2, visibility="public", tags=[tag2])
        url = reverse("posts:article-list")

        # Guests must only ever see public articles in list responses
        guest_list = self.client.get(url, format="json")
        self.assertEqual(guest_list.status_code, status.HTTP_200_OK)
        self.assertEqual(len(guest_list.data["data"]), 2)
        guest_ids = {item["id"] for item in guest_list.data["data"]}
        self.assertNotIn(private_article.pk, guest_ids)
        self.assertNotIn(unlisted_article.pk, guest_ids)

        guest_private = self.client.get(url, {"visibility": "private"}, format="json")
        self.assertEqual(guest_private.status_code, status.HTTP_200_OK)
        self.assertEqual(len(guest_private.data["data"]), 0)

        # Staff users can filter across private/unlisted/public articles
        self._authenticate_as_staff()

        # Filter by series
        response = self.client.get(url, {"series": series.pk}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)

        # Filter by visibility
        response = self.client.get(url, {"visibility": "public"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)

        # Filter by category
        response = self.client.get(url, {"category": category.slug}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)

        # Filter by tags
        response = self.client.get(url, {"tags": tag1.slug}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)

        response = self.client.get(url, {"tags": tag2.slug}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)

    def test_article_is_hot_filtering(self):
        # Hot article: recent, high views
        ArticleFactory(
            published_at=timezone.now() - timedelta(days=15), views_count=2000
        )
        # Not hot article: old
        ArticleFactory(
            published_at=timezone.now() - timedelta(days=45), views_count=2000
        )
        # Not hot article: low views
        ArticleFactory(
            published_at=timezone.now() - timedelta(days=15), views_count=500
        )
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

        url = reverse(
            "posts:article-by-slug", kwargs={"slug": article.translation.slug}
        )
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
        url = reverse(
            "posts:article-related", kwargs={"slug": article.translation.slug}
        )
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

    def test_guest_visibility_access_control(self):
        category = CategoryFactory()
        tag = TagFactory()
        public_article = ArticleFactory(
            status="published",
            visibility="public",
            category=category,
            tags=[tag],
        )
        private_article = ArticleFactory(
            status="published",
            visibility="private",
            category=category,
            tags=[tag],
        )
        unlisted_article = ArticleFactory(
            status="published",
            visibility="unlisted",
            category=category,
            tags=[tag],
        )

        # Guests get 404 for private articles via detail and by-slug
        private_detail = reverse(
            "posts:article-detail", kwargs={"slug": private_article.translation.slug}
        )
        private_by_slug = reverse(
            "posts:article-by-slug", kwargs={"slug": private_article.translation.slug}
        )
        self.assertEqual(
            self.client.get(private_detail).status_code, status.HTTP_404_NOT_FOUND
        )
        self.assertEqual(
            self.client.get(private_by_slug).status_code, status.HTTP_404_NOT_FOUND
        )

        # Guests CAN access published unlisted articles directly by slug/detail
        unlisted_detail = reverse(
            "posts:article-detail", kwargs={"slug": unlisted_article.translation.slug}
        )
        unlisted_by_slug = reverse(
            "posts:article-by-slug", kwargs={"slug": unlisted_article.translation.slug}
        )
        self.assertEqual(self.client.get(unlisted_detail).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(unlisted_by_slug).status_code, status.HTTP_200_OK)

        # Similar, same-category, and related endpoints must exclude private & unlisted
        similar_url = reverse(
            "posts:article-similar", kwargs={"slug": public_article.translation.slug}
        )
        same_cat_url = reverse(
            "posts:article-same-category",
            kwargs={"slug": public_article.translation.slug},
        )
        related_url = reverse(
            "posts:article-related", kwargs={"slug": public_article.translation.slug}
        )

        self.assertEqual(self.client.get(similar_url).data, [])
        self.assertEqual(self.client.get(same_cat_url).data["data"], [])
        self.assertEqual(self.client.get(related_url).data["data"], [])

    def test_article_is_hot_editorial_flag(self):
        editorial_hot = ArticleFactory(
            status="published",
            visibility="public",
            is_hot=True,
            published_at=timezone.now() - timedelta(days=90),
            views_count=10,
        )
        regular_article = ArticleFactory(
            status="published",
            visibility="public",
            is_hot=False,
            published_at=timezone.now() - timedelta(days=90),
            views_count=10,
        )
        url = reverse("posts:article-list")

        hot_res = self.client.get(url, {"is_hot": "true"}, format="json")
        self.assertEqual(hot_res.status_code, status.HTTP_200_OK)
        hot_ids = {item["id"] for item in hot_res.data["data"]}
        self.assertIn(editorial_hot.pk, hot_ids)
        self.assertNotIn(regular_article.pk, hot_ids)

        not_hot_res = self.client.get(url, {"is_hot": "false"}, format="json")
        self.assertEqual(not_hot_res.status_code, status.HTTP_200_OK)
        not_hot_ids = {item["id"] for item in not_hot_res.data["data"]}
        self.assertNotIn(editorial_hot.pk, not_hot_ids)
        self.assertIn(regular_article.pk, not_hot_ids)

    def test_article_normalized_persian_arabic_search(self):
        article = ArticleFactory(
            status="published",
            visibility="public",
            translation__language_code="fa",
            translation__title="راهنماي جامع فيفا ۲۶ و كالاف دیوتی",
            translation__excerpt="تنظيمات كنسول بازي",
            translation__content="آموزش كامل فيفا ۲۶ در گیم‌نت",
        )
        url = reverse("posts:article-list")

        # Search using Persian Yeh/Kaf and ASCII digits instead of Arabic letters / Persian digits
        response = self.client.get(
            url, {"search": "فیفا 26 کالاف", "lang": "fa"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = {item["id"] for item in response.data["data"]}
        self.assertIn(article.pk, result_ids)

    def test_persian_auto_unique_slug_and_unicode_routes(self):
        self._authenticate_as_staff()
        tag = TagFactory(name="یادگیری ماشین")
        list_url = reverse("posts:article-list")

        payload = {
            "language_code": "fa",
            "title": "آموزش هوش مصنوعی",
            "excerpt": "خلاصه مقاله فارسی",
            "content": "محتوای کامل مقاله فارسی.",
            "status": "draft",
            "tag_ids": [tag.pk],
        }
        r1 = self.client.post(list_url, payload, format="json")
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r1.data["slug"], "آموزش-هوش-مصنوعی")

        r2 = self.client.post(list_url, {**payload, "slug": ""}, format="json")
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r2.data["slug"], "آموزش-هوش-مصنوعی-2")

        r3 = self.client.post(list_url, payload, format="json")
        self.assertEqual(r3.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r3.data["slug"], "آموزش-هوش-مصنوعی-3")

        slug1 = r1.data["slug"]
        detail_url = reverse("posts:article-detail", kwargs={"slug": slug1})
        self.assertEqual(
            self.client.get(detail_url, {"lang": "fa"}).status_code,
            status.HTTP_200_OK,
        )

        by_slug_url = reverse("posts:article-by-slug", kwargs={"slug": slug1})
        by_slug_res = self.client.get(by_slug_url, {"lang": "fa"})
        self.assertEqual(by_slug_res.status_code, status.HTTP_200_OK)
        self.assertEqual(by_slug_res.data["id"], r1.data["id"])

        patch_res = self.client.patch(
            detail_url, {"title": "آموزش هوش مصنوعی پیشرفته"}, format="json"
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data["slug"], slug1)

        publish_url = reverse("posts:article-publish", kwargs={"slug": slug1})
        pub_res = self.client.post(publish_url)
        self.assertEqual(pub_res.status_code, status.HTTP_200_OK)
        self.assertEqual(pub_res.data["status"], "published")

        related_url = reverse("posts:article-related", kwargs={"slug": slug1})
        rel_res = self.client.get(related_url)
        self.assertEqual(rel_res.status_code, status.HTTP_200_OK)
