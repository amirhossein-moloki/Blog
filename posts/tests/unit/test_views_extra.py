from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from posts.models import (
    Article,
    ArticleTranslation,
    AuthorProfile,
    Category,
    Revision,
    Tag,
)
from users.models import User


class ArticleViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="author", password="password")
        self.author_profile = AuthorProfile.objects.create(
            user=self.user, display_name="Author"
        )
        self.admin = User.objects.create_superuser(
            username="admin", password="password", email="admin@example.com"
        )
        self.category = Category.objects.create(name="Tech", slug="tech")
        self.tag = Tag.objects.create(name="Django", slug="django")
        self.article = Article.objects.create(
            author=self.author_profile,
            category=self.category,
            status="published",
            published_at=timezone.now() - timedelta(days=1),
        )
        ArticleTranslation.objects.create(
            article=self.article,
            language_code="en",
            title="Initial Article",
            slug="initial-article",
            content="Some content",
            excerpt="Some excerpt",
        )
        self.article.tags.add(self.tag)
        self.list_url = reverse("posts:article-list")
        self.detail_url = reverse(
            "posts:article-detail", kwargs={"slug": self.article.translation.slug}
        )

    def test_get_queryset_fields_select_related(self):
        # Testing the custom field selection logic in get_queryset
        url = self.list_url + "?fields=author,category,likes_count"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_queryset_staff_bypass(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_queryset_authenticated_filter(self):
        self.client.force_authenticate(user=self.user)
        # Create a draft by another author (won't exist but for coverage)
        other_user = User.objects.create_user(username="other", password="password")
        other_author = AuthorProfile.objects.create(
            user=other_user, display_name="Other"
        )
        other_article = Article.objects.create(author=other_author, status="draft")
        ArticleTranslation.objects.create(
            article=other_article,
            language_code="en",
            title="Other Draft",
            slug="other-draft",
            excerpt="Excerpt",
            content="Content",
        )

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should see self draft and published articles

    def test_perform_create_no_author_profile(self):
        user_no_profile = User.objects.create_user(
            username="noprofile", password="password"
        )
        self.client.force_authenticate(user=user_no_profile)
        data = {"title": "New Article", "content": "Content", "status": "draft"}
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_similar_articles(self):
        url = reverse(
            "posts:article-similar", kwargs={"slug": self.article.translation.slug}
        )
        # Article with same category
        similar_article = Article.objects.create(
            author=self.author_profile,
            category=self.category,
            status="published",
            published_at=timezone.now(),
        )
        ArticleTranslation.objects.create(
            article=similar_article,
            language_code="en",
            title="Similar Article",
            slug="similar-article",
            excerpt="Excerpt",
            content="Content",
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"] if "data" in response.data else response.data
        self.assertEqual(len(data), 1)

    def test_similar_articles_no_category(self):
        article_no_cat = Article.objects.create(
            author=self.author_profile,
            status="published",
        )
        article_no_cat_trans = ArticleTranslation.objects.create(
            article=article_no_cat,
            language_code="en",
            title="No Cat",
            slug="no-cat",
            excerpt="Excerpt",
            content="Content",
        )
        url = reverse(
            "posts:article-similar", kwargs={"slug": article_no_cat_trans.slug}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"] if "data" in response.data else response.data
        self.assertEqual(data, [])

    def test_perform_create_success(self):
        self.client.force_authenticate(user=self.user)
        data = {
            "title": "New Article 2",
            "excerpt": "Excerpt",
            "content": "Content",
            "status": "draft",
        }
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_revision_list(self):
        self.client.force_authenticate(user=self.admin)
        Revision.objects.create(
            article=self.article,
            title="Old Title",
            excerpt="Old Excerpt",
            content="Old Content",
            editor=self.user,
        )
        url = reverse("posts:revision-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_same_category_no_category(self):
        article_no_cat = Article.objects.create(
            author=self.author_profile,
            status="published",
        )
        article_no_cat_trans = ArticleTranslation.objects.create(
            article=article_no_cat,
            language_code="en",
            title="No Cat 2",
            slug="no-cat-2",
            excerpt="Excerpt",
            content="Content",
        )
        url = reverse(
            "posts:article-same-category", kwargs={"slug": article_no_cat_trans.slug}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"] if "data" in response.data else response.data
        self.assertEqual(data, [])

    def test_by_slug_not_found(self):
        url = reverse("posts:article-by-slug", kwargs={"slug": "non-existent"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_similar_not_found(self):
        # We need a slug that doesn't exist but matches the URL pattern
        url = reverse("posts:article-similar", kwargs={"slug": "non-existent"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_publish_article_not_found(self):
        url = reverse("posts:article-publish", kwargs={"slug": "non-existent"})
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_related_articles_not_found(self):
        url = reverse("posts:article-related", kwargs={"slug": "non-existent"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_publish_article_api(self):
        draft = Article.objects.create(author=self.author_profile, status="draft")
        draft_trans = ArticleTranslation.objects.create(
            article=draft,
            language_code="en",
            title="Draft",
            slug="draft-article",
            excerpt="Excerpt",
            content="Content",
        )
        self.client.force_authenticate(user=self.user)
        url = reverse("posts:article-publish", kwargs={"slug": draft_trans.slug})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        draft.refresh_from_db()
        self.assertEqual(draft.status, "published")

    def test_publish_article_api_unauthorized(self):
        other_user = User.objects.create_user(username="other2", password="password")
        draft = Article.objects.create(
            author=self.author_profile,
            status="draft",
        )
        draft_trans = ArticleTranslation.objects.create(
            article=draft,
            language_code="en",
            title="Draft 2",
            slug="draft-article-2",
            excerpt="Excerpt",
            content="Content",
        )
        self.client.force_authenticate(user=other_user)
        url = reverse("posts:article-publish", kwargs={"slug": draft_trans.slug})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_publish_article_api_invalid_status(self):
        self.client.force_authenticate(user=self.user)
        url = reverse(
            "posts:article-publish", kwargs={"slug": self.article.translation.slug}
        )  # Already published
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_related_articles_no_tags(self):
        article_no_tags = Article.objects.create(
            author=self.author_profile,
            status="published",
        )
        article_no_tags_trans = ArticleTranslation.objects.create(
            article=article_no_tags,
            language_code="en",
            title="No Tags",
            slug="no-tags",
            excerpt="Excerpt",
            content="Content",
        )
        url = reverse(
            "posts:article-related", kwargs={"slug": article_no_tags_trans.slug}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"] if "data" in response.data else response.data
        self.assertEqual(data, [])


class ArticleSerializerTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="author2", password="password")
        self.author_profile = AuthorProfile.objects.create(
            user=self.user, display_name="Author 2"
        )
        self.admin = User.objects.create_superuser(
            username="admin2", password="password", email="admin2@example.com"
        )

    def test_handle_publication_date_scheduled(self):
        from posts.serializers import ArticleCreateUpdateSerializer

        future_date = timezone.now() + timedelta(days=1)
        data = {
            "title": "Scheduled Article",
            "excerpt": "Excerpt",
            "content": "Content",
            "status": "published",
            "publish_at": future_date,
        }
        serializer = ArticleCreateUpdateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        article = serializer.save(author=self.author_profile)
        self.assertEqual(article.status, "scheduled")
        self.assertEqual(article.scheduled_at, future_date)

    def test_handle_publication_date_past(self):
        from posts.serializers import ArticleCreateUpdateSerializer

        past_date = timezone.now() - timedelta(days=1)
        data = {
            "title": "Past Article",
            "excerpt": "Excerpt",
            "content": "Content",
            "status": "published",
            "publish_at": past_date,
        }
        serializer = ArticleCreateUpdateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        article = serializer.save(author=self.author_profile)
        self.assertEqual(article.status, "published")
        self.assertEqual(article.published_at, past_date)

    def test_handle_publication_date_draft_future(self):
        from posts.serializers import ArticleCreateUpdateSerializer

        future_date = timezone.now() + timedelta(days=1)
        data = {
            "title": "Draft Scheduled",
            "excerpt": "Excerpt",
            "content": "Content",
            "status": "draft",
            "publish_at": future_date,
        }
        serializer = ArticleCreateUpdateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        article = serializer.save(author=self.author_profile)
        self.assertEqual(article.status, "draft")
        self.assertEqual(article.scheduled_at, future_date)

    def test_handle_publication_date_draft_past(self):
        from posts.serializers import ArticleCreateUpdateSerializer

        past_date = timezone.now() - timedelta(days=1)
        data = {
            "title": "Draft Past",
            "excerpt": "Excerpt",
            "content": "Content",
            "status": "draft",
            "publish_at": past_date,
        }
        serializer = ArticleCreateUpdateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        article = serializer.save(author=self.author_profile)
        self.assertEqual(article.status, "draft")
        self.assertIsNone(article.scheduled_at)

    def test_jalali_date_field_none(self):
        from posts.serializers import JalaliDateTimeField

        field = JalaliDateTimeField()
        self.assertIsNone(field.to_representation(None))

    def test_ckeditor_upload_view(self):
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        file = io.BytesIO()
        image = Image.new("RGB", size=(10, 10), color=(155, 0, 0))
        image.save(file, "png")
        file.name = "test.png"
        file.seek(0)
        uploaded_file = SimpleUploadedFile(
            file.name, file.read(), content_type="image/png"
        )

        url = reverse("ckeditor_upload")
        self.client.force_login(user=self.admin)
        response = self.client.post(url, {"upload": uploaded_file}, format="multipart")
        self.assertEqual(response.status_code, 200)
        self.assertIn("url", response.json())

    def test_ckeditor_upload_view_no_file(self):
        url = reverse("ckeditor_upload")
        self.client.force_login(user=self.admin)
        response = self.client.post(url, {}, format="multipart")
        self.assertEqual(response.status_code, 400)

    def test_ckeditor_upload_view_not_image(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        uploaded_file = SimpleUploadedFile(
            "test.txt", b"not image", content_type="text/plain"
        )
        url = reverse("ckeditor_upload")
        self.client.force_login(user=self.admin)
        response = self.client.post(url, {"upload": uploaded_file}, format="multipart")
        self.assertEqual(response.status_code, 400)

    def test_ckeditor_upload_view_unauthorized(self):
        user_no_profile = User.objects.create_user(
            username="noprofile2", password="password"
        )
        url = reverse("ckeditor_upload")
        self.client.force_login(user=user_no_profile)
        response = self.client.post(url, {}, format="multipart")
        self.assertIn(response.status_code, [403, 302])


class ArticleUnifiedWorkflowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="author_wf", password="password")
        self.author_profile = AuthorProfile.objects.create(
            user=self.user, display_name="Workflow Author"
        )
        self.list_url = reverse("posts:article-list")

    def _create_dummy_image(self, name):
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        file = io.BytesIO()
        image = Image.new("RGB", size=(10, 10), color=(0, 120, 0))
        image.save(file, "png")
        file.name = name
        file.seek(0)
        return SimpleUploadedFile(name, file.read(), content_type="image/png")

    def test_new_workflow_multipart_success(self):
        import json

        self.client.force_authenticate(user=self.user)

        # Create dummy files
        cover_image = self._create_dummy_image("cover.png")
        og_image = self._create_dummy_image("og.png")
        img1 = self._create_dummy_image("content1.png")
        gallery1 = self._create_dummy_image("gallery1.png")

        article_data = {
            "title": "Unified Workflow Test",
            "excerpt": "This is an excerpt",
            "content": '<p>Hello</p><img data-upload-id="img1"><p>World</p>',
            "status": "draft",
        }

        payload = {
            "article": json.dumps(article_data),
            "cover_image": cover_image,
            "og_image": og_image,
            "files[img1]": img1,
            "files[gallery1]": gallery1,
        }

        response = self.client.post(self.list_url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check database records
        article = Article.objects.get(id=response.data["id"])
        self.assertIsNotNone(article.cover_image)
        self.assertIsNotNone(article.og_image)

        # Check translation and content replacement
        translation = article.translations.get(language_code="en")
        self.assertNotIn("data-upload-id", translation.content)
        self.assertIn('src="', translation.content)
        self.assertIn("content1", translation.content)

        # Check ArticleMedia relationships
        attachments = article.media_attachments.all()
        attachment_types = [a.attachment_type for a in attachments]
        self.assertIn("cover", attachment_types)
        self.assertIn("og-image", attachment_types)
        self.assertIn("in-content", attachment_types)
        self.assertIn("gallery", attachment_types)

    def test_legacy_workflow_backward_compatibility(self):
        self.client.force_authenticate(user=self.user)

        from medias.models import ArticleMedia, Media

        # Manually create media first
        cover_media = Media.objects.create(
            storage_key="cover.png",
            url="/media/cover.png",
            type="image",
            mime="image/png",
            uploaded_by=self.user,
        )

        payload = {
            "title": "Legacy Test Article",
            "excerpt": "Legacy excerpt",
            "content": "<p>Legacy content</p>",
            "status": "draft",
            "cover_image_id": cover_media.id,
        }

        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        article = Article.objects.get(id=response.data["id"])
        self.assertEqual(article.cover_image, cover_media)

        # Verify cover relationship is synced
        self.assertTrue(
            ArticleMedia.objects.filter(
                article=article, media=cover_media, attachment_type="cover"
            ).exists()
        )

    def test_transaction_rollback_and_storage_cleanup_on_failure(self):
        import json

        self.client.force_authenticate(user=self.user)

        cover_image = self._create_dummy_image("fail_cover.png")

        # Excerpt is a required field, omitting it will cause validation failure in the serializer
        article_data = {
            "title": "Failure Test Article",
            "content": "<p>Will Fail</p>",
            "status": "draft",
        }

        payload = {
            "article": json.dumps(article_data),
            "cover_image": cover_image,
        }

        from medias.models import Media

        # Capture pre-existing keys to verify no leaks
        pre_existing_medias_count = Media.objects.count()

        response = self.client.post(self.list_url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Ensure no new Media records are persistent in the DB (rolled back)
        self.assertEqual(Media.objects.count(), pre_existing_medias_count)

    def test_new_workflow_invalid_file_extension(self):
        import json
        self.client.force_authenticate(user=self.user)

        from django.core.files.uploadedfile import SimpleUploadedFile
        invalid_file = SimpleUploadedFile("danger.exe", b"binarycontent", content_type="application/octet-stream")

        article_data = {
            "title": "Invalid Extension Article",
            "excerpt": "This is an excerpt",
            "content": "<p>Content</p>",
            "status": "draft",
        }

        payload = {
            "article": json.dumps(article_data),
            "cover_image": invalid_file,
        }

        response = self.client.post(self.list_url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(any("cover_image" in msg for msg in response.data.get("messagesList", [])))

    def test_new_workflow_file_too_large(self):
        import json
        self.client.force_authenticate(user=self.user)

        from django.core.files.uploadedfile import SimpleUploadedFile
        # 11 MB of zero bytes
        large_file = SimpleUploadedFile("large_image.jpg", b"0" * (11 * 1024 * 1024), content_type="image/jpeg")

        article_data = {
            "title": "Too Large Article",
            "excerpt": "This is an excerpt",
            "content": "<p>Content</p>",
            "status": "draft",
        }

        payload = {
            "article": json.dumps(article_data),
            "cover_image": large_file,
        }

        response = self.client.post(self.list_url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(any("cover_image" in msg for msg in response.data.get("messagesList", [])))
