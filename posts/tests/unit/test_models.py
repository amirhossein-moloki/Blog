from django.contrib.auth import get_user_model
from django.test import TestCase

from posts.factories import AuthorProfileFactory, CategoryFactory, PostFactory
from posts.models import Post, PostTranslation

User = get_user_model()


class PostModelTests(TestCase):
    def test_post_reading_time_calculation(self):
        # 200 words should be around 1 minute (60 seconds)
        content = "word " * 200
        author = AuthorProfileFactory()
        post = Post.objects.create(author=author)
        pt = PostTranslation.objects.create(
            post=post,
            language_code="en",
            title="Test Post",
            slug="test-post",
            content=content,
            excerpt="Excerpt",
        )
        self.assertEqual(pt.reading_time_sec, 60)

    def test_post_reading_time_empty_content(self):
        author = AuthorProfileFactory()
        post = Post.objects.create(author=author)
        pt = PostTranslation.objects.create(
            post=post,
            language_code="en",
            title="Test Post",
            slug="test-post-empty",
            content="",
            excerpt="Excerpt",
        )
        self.assertEqual(pt.reading_time_sec, 0)

    def test_post_str(self):
        post = PostFactory(translation__title="Unique Title")
        self.assertEqual(str(post.translation), "Unique Title (en)")


class AuthorProfileModelTests(TestCase):
    def test_author_profile_str(self):
        author = AuthorProfileFactory(display_name="John Doe")
        self.assertEqual(str(author), "John Doe")


class CategoryModelTests(TestCase):
    def test_category_str(self):
        category = CategoryFactory(name="Tech")
        self.assertEqual(str(category), "Tech")
