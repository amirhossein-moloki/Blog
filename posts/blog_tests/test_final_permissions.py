from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile

from posts.blog_tests.base import BaseAPITestCase
from posts.factories import (
    ArticleFactory,
    AuthorProfileFactory,
    CategoryFactory,
    MediaFactory,
    RevisionFactory,
    UserFactory,
)
from posts.models import Article, AuthorProfile
from medias.models import Media

User = get_user_model()


class FinalPermissionsAPITest(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.category = CategoryFactory()
        self.article = ArticleFactory(category=self.category, status="published")

        # self.user from BaseAPITestCase has an author_profile, so they act as "author_user"
        # Let's create a separate regular user who DOES NOT have an author profile
        self.regular_user = UserFactory()
        AuthorProfile.objects.filter(user=self.regular_user).delete()

        # Create a standalone author user and profile
        self.author_user = self.user  # self.user has self.author_profile

    def _create_dummy_image(self, name="test.jpg", content_type="image/jpeg"):
        image_io = BytesIO()
        image = Image.new("RGB", (100, 100), color="blue")
        image.save(image_io, "jpeg")
        image_io.seek(0)
        return SimpleUploadedFile(name, image_io.getvalue(), content_type=content_type)

    # ==========================
    # 1. ARTICLES PERMISSIONS
    # ==========================
    def test_articles_public_readable(self):
        # Anonymous user can list articles
        response = self.client.get(reverse("posts:article-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Anonymous user can retrieve article detail
        url = reverse(
            "posts:article-detail", kwargs={"slug": self.article.translation.slug}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_articles_create_permissions(self):
        url = reverse("posts:article-list")
        data = {
            "title": "New Public Content",
            "slug": "new-public-content",
            "excerpt": "Excerpt",
            "content": "Content",
        }

        # Anonymous gets 401
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Regular authenticated user gets 403
        self._authenticate(self.regular_user)
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Author gets 201
        self._authenticate(self.author_user)
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Admin gets 201
        self._authenticate_as_staff()
        data["slug"] = "new-public-content-admin"
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_articles_delete_strictly_restricted_to_admin(self):
        # Create an article owned by author_profile
        article = ArticleFactory(author=self.author_profile)
        url = reverse("posts:article-detail", kwargs={"slug": article.translation.slug})

        # Anonymous gets 401
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Regular user gets 403
        self._authenticate(self.regular_user)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Author trying to delete their OWN article gets 403
        self._authenticate(self.author_user)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Admin gets 204
        self._authenticate_as_staff()
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    # ==========================
    # 2. AUTHORS PERMISSIONS
    # ==========================
    def test_authors_public_readable(self):
        # Anonymous user can list author profiles
        response = self.client.get(reverse("posts:authorprofile-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authors_create_admin_only(self):
        url = reverse("posts:authorprofile-list")
        new_user = UserFactory()
        data = {
            "user": new_user.pk,
            "display_name": "Test Writer",
        }

        # Anonymous gets 401
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Regular user gets 403
        self._authenticate(self.regular_user)
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Admin gets 201
        self._authenticate_as_staff()
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # ==========================
    # 3. MEDIA PERMISSIONS
    # ==========================
    def test_media_list_blocked_publicly(self):
        url = reverse("medias:media-list")

        # Anonymous gets 401
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Regular user gets 403
        self._authenticate(self.regular_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Author gets 200
        self._authenticate(self.author_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Admin gets 200
        self._authenticate_as_staff()
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_media_upload_permissions(self):
        url = reverse("medias:media-list")
        image = self._create_dummy_image()

        # Anonymous gets 401
        response = self.client.post(url, {"file": image}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Regular user gets 403
        self._authenticate(self.regular_user)
        image.seek(0)
        response = self.client.post(url, {"file": image}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Author gets 201
        self._authenticate(self.author_user)
        image.seek(0)
        response = self.client.post(url, {"file": image}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # ==========================
    # 4. REVISIONS PERMISSIONS
    # ==========================
    def test_revisions_admin_only(self):
        article = ArticleFactory()
        revision = RevisionFactory(article=article)
        url_list = reverse("posts:revision-list")
        url_detail = reverse("posts:revision-detail", kwargs={"pk": revision.pk})

        # Anonymous gets 401
        response = self.client.get(url_list)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = self.client.get(url_detail)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Regular user gets 403
        self._authenticate(self.regular_user)
        response = self.client.get(url_list)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.get(url_detail)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Author gets 403
        self._authenticate(self.author_user)
        response = self.client.get(url_list)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.get(url_detail)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Admin gets 200
        self._authenticate_as_staff()
        response = self.client.get(url_list)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.get(url_detail)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ==========================
    # 5. COMMENTS PERMISSIONS
    # ==========================
    def test_comments_public_readable(self):
        # Anonymous user can list comments
        url = reverse("interactions:comment-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("interactions.tasks.notify_author_on_new_comment.delay")
    def test_comments_create_requires_auth(self, mock_task):
        url = reverse("interactions:comment-list")
        data = {
            "article": self.article.pk,
            "author_name": "Commenter",
            "author_email": "commenter@example.com",
            "content": "Nice article!",
        }

        # Anonymous gets 401
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Authenticated user gets 201
        self._authenticate(self.regular_user)
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
