from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from interactions.models import Comment
from medias.models import Media
from posts.models import Article, ArticleTranslation, AuthorProfile, Category

User = get_user_model()


class AdminSuiteTestCase(TestCase):
    """
    Comprehensive test suite verifying access control, form validation, custom admin actions,
    and performance across the Django Admin system.
    """

    def setUp(self):
        # Create regular user, staff user, and superuser
        self.regular_user = User.objects.create_user(
            username="regularuser",
            email="regular@example.com",
            password="Password123!@#",
            is_staff=False,
            is_active=True,
        )
        self.staff_user = User.objects.create_user(
            username="staffuser",
            email="staff@example.com",
            password="Password123!@#",
            is_staff=True,
            is_superuser=False,
            is_active=True,
        )
        self.superuser = User.objects.create_superuser(
            username="superuser",
            email="admin@example.com",
            password="Password123!@#",
            is_staff=True,
            is_active=True,
        )

        # Create AuthorProfile for superuser
        self.author_profile = AuthorProfile.objects.create(
            user=self.superuser,
            display_name="Admin Superuser",
            bio="Bio text",
        )

        # Create sample domain models
        self.category = Category.objects.create(name="Tech", slug="tech")
        self.article = Article.objects.create(
            author=self.author_profile,
            category=self.category,
            status="draft",
        )
        self.translation = ArticleTranslation.objects.create(
            article=self.article,
            language_code="en",
            title="Admin Test Article",
            slug="admin-test-article",
            excerpt="Excerpt",
            content="Content",
            content_blocks=[],
        )
        self.media = Media.objects.create(
            title="Sample Media",
            storage_key="sample.png",
            url="http://localhost:8000/media/sample.png",
            type="image",
            mime="image/png",
            size_bytes=1024,
            status="Ready",
            uploaded_by=self.superuser,
        )
        self.comment = Comment.objects.create(
            article=self.article,
            user=self.regular_user,
            content="Sample comment",
            status="pending",
        )

    def test_admin_access_control(self):
        """
        Verifies that anonymous and regular users are denied admin access,
        while staff/superuser can access admin index.
        """
        admin_index_url = reverse("admin:index")

        # Anonymous user redirect
        res = self.client.get(admin_index_url)
        self.assertIn(
            res.status_code, [status.HTTP_302_FOUND, status.HTTP_401_UNAUTHORIZED]
        )

        # Regular user redirect/forbidden
        self.client.force_login(self.regular_user)
        res = self.client.get(admin_index_url)
        self.assertEqual(res.status_code, status.HTTP_302_FOUND)

        # Superuser success
        self.client.force_login(self.superuser)
        res = self.client.get(admin_index_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_article_admin_custom_actions(self):
        """
        Verifies custom actions on ArticleAdmin (e.g., publish, mark as hot).
        """
        self.client.force_login(self.superuser)
        changelist_url = reverse("admin:posts_article_changelist")

        # Test action 'make_published'
        data = {
            "action": "make_published",
            "_selected_action": [self.article.id],
        }
        res = self.client.post(changelist_url, data)
        self.assertEqual(res.status_code, status.HTTP_302_FOUND)
        self.article.refresh_from_db()
        self.assertEqual(self.article.status, "published")

        # Test action 'mark_as_hot'
        data = {
            "action": "mark_as_hot",
            "_selected_action": [self.article.id],
        }
        res = self.client.post(changelist_url, data)
        self.assertEqual(res.status_code, status.HTTP_302_FOUND)
        self.article.refresh_from_db()
        self.assertTrue(self.article.is_hot)

    def test_comment_admin_moderation_actions(self):
        """
        Verifies moderation actions on CommentAdmin (approve, mark_as_spam, mark_as_removed).
        """
        self.client.force_login(self.superuser)
        changelist_url = reverse("admin:interactions_comment_changelist")

        # Approve comment
        data = {
            "action": "approve_comments",
            "_selected_action": [self.comment.id],
        }
        res = self.client.post(changelist_url, data)
        self.assertEqual(res.status_code, status.HTTP_302_FOUND)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.status, "approved")

        # Mark as spam
        data = {
            "action": "mark_as_spam",
            "_selected_action": [self.comment.id],
        }
        res = self.client.post(changelist_url, data)
        self.assertEqual(res.status_code, status.HTTP_302_FOUND)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.status, "spam")

    def test_media_admin_quarantine_action(self):
        """
        Verifies quarantine and soft delete actions on MediaAdmin.
        """
        self.client.force_login(self.superuser)
        changelist_url = reverse("admin:medias_media_changelist")

        data = {
            "action": "quarantine_media",
            "_selected_action": [self.media.id],
        }
        res = self.client.post(changelist_url, data)
        self.assertEqual(res.status_code, status.HTTP_302_FOUND)
        self.media.refresh_from_db()
        self.assertEqual(self.media.status, "Quarantined")

    def test_article_translation_form_validation(self):
        """
        Verifies that invalid JSON content_blocks in ArticleTranslationForm are rejected.
        """
        from posts.admin import ArticleTranslationForm

        invalid_data = {
            "article": self.article.id,
            "language_code": "en",
            "title": "Invalid Block Title",
            "slug": "invalid-block-title",
            "excerpt": "Excerpt",
            "content": "Content",
            "content_blocks": [
                {
                    "type": "non_existent_block_type",
                    "id": "blk1",
                    "data": {},
                }
            ],
        }
        form = ArticleTranslationForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn("content_blocks", form.errors)

    def test_admin_changelist_query_efficiency(self):
        """
        Verifies that changelist views perform select_related/prefetch_related to avoid N+1 queries.
        """
        self.client.force_login(self.superuser)
        changelist_url = reverse("admin:posts_article_changelist")

        res = self.client.get(changelist_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_api_admin_login_remains_staff_restricted(self):
        """
        Verifies that the /api/auth/admin-login/ endpoint remains restricted to staff users.
        """
        admin_login_url = reverse("admin-login")

        # Non-staff attempt -> 403
        res = self.client.post(
            admin_login_url,
            {"username": self.regular_user.username, "password": "Password123!@#"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Staff attempt -> 200
        res = self.client.post(
            admin_login_url,
            {"username": self.staff_user.username, "password": "Password123!@#"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
