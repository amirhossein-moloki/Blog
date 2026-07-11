from io import StringIO
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from medias.models import Media
from posts.factories import UserFactory
from posts.models import Article, AuthorProfile

User = get_user_model()


class CreateRandomArticlesTest(TestCase):

    def setUp(self):
        super().setUp()

        # Create a mock for requests.get that will be used in all tests
        self.patcher = patch("requests.get")
        self.mock_get = self.patcher.start()

        # Configure the mock to return a successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake-image-content"
        mock_response.raise_for_status.return_value = None
        self.mock_get.return_value = mock_response

    def tearDown(self):
        # Stop the patcher to clean up
        self.patcher.stop()
        super().tearDown()

    def test_command_creates_articles(self):
        """Test that the command creates the specified number of articles."""
        out = StringIO()
        # Ensure at least one author profile exists for the command to use
        user = UserFactory()
        AuthorProfile.objects.create(user=user, display_name=user.username)

        call_command("create_random_articles", "5", stdout=out)

        self.assertEqual(Article.objects.count(), 5, "Should create 5 articles")
        self.assertIn("Successfully created 5 random articles.", out.getvalue())
        self.assertEqual(
            self.mock_get.call_count,
            10,
            "Should call requests.get 10 times (2 images per article)",
        )
        self.assertEqual(Media.objects.count(), 10, "Should create 10 media objects")

        # Verify article.translation.content
        for article in Article.objects.all():
            self.assertTrue(article.translation.title)
            self.assertTrue(article.translation.content)
            self.assertTrue(article.translation.excerpt)
            self.assertIsNotNone(article.author)
            self.assertIsNotNone(article.category)
            self.assertTrue(article.tags.exists())
            self.assertIn(article.status, ["draft", "published"])
            self.assertIsNotNone(article.cover_image)
            self.assertIsNotNone(article.og_image)

    def test_command_creates_user_if_none_exist(self):
        """Test that the command creates a default user if no users exist."""
        User.objects.all().delete()
        self.assertEqual(User.objects.count(), 0)

        out = StringIO()
        call_command("create_random_articles", "1", stdout=out)

        self.assertEqual(User.objects.count(), 1, "Should create a default user")
        # The command should also create an AuthorProfile for the new user
        self.assertTrue(AuthorProfile.objects.exists())
        self.assertEqual(Article.objects.count(), 1, "Should create 1 article")
        self.assertEqual(
            self.mock_get.call_count, 2, "Should call requests.get 2 times"
        )

    def test_command_uses_existing_users(self):
        """Test that the command uses existing users to create articles."""
        user1 = UserFactory()
        # Manually create the AuthorProfile since the signal is disabled
        author_profile, _ = AuthorProfile.objects.get_or_create(
            user=user1, defaults={"display_name": "User One"}
        )
        author_profile.display_name = "User One"
        author_profile.save()

        call_command("create_random_articles", "3")

        self.assertEqual(Article.objects.count(), 3)
        created_articles_authors = [p.author.user for p in Article.objects.all()]
        self.assertIn(user1, created_articles_authors)
        self.assertEqual(
            self.mock_get.call_count, 6, "Should call requests.get 6 times"
        )
