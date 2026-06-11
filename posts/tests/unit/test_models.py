from django.contrib.auth import get_user_model
from django.test import TestCase

from posts.factories import AuthorProfileFactory, CategoryFactory, PostFactory
from posts.models import Post

User = get_user_model()


class PostModelTests(TestCase):
    def test_post_reading_time_calculation(self):
        # 200 words should be around 1 minute (60 seconds)
        content = "word " * 200
        author = AuthorProfileFactory()
        post = Post.objects.create(
            title="Test Post",
            slug="test-post",
            content=content,
            author=author,
            excerpt="Excerpt",
        )
        self.assertEqual(post.reading_time_sec, 60)

    def test_post_reading_time_empty_content(self):
        author = AuthorProfileFactory()
        post = Post.objects.create(
            title="Test Post",
            slug="test-post-empty",
            content="",
            author=author,
            excerpt="Excerpt",
        )
        self.assertEqual(post.reading_time_sec, 0)

    def test_post_str(self):
        post = PostFactory(title="Unique Title")
        self.assertEqual(str(post), "Unique Title")


class AuthorProfileModelTests(TestCase):
    def test_author_profile_str(self):
        author = AuthorProfileFactory(display_name="John Doe")
        self.assertEqual(str(author), "John Doe")


class CategoryModelTests(TestCase):
    def test_category_str(self):
        category = CategoryFactory(name="Tech")
        self.assertEqual(str(category), "Tech")
