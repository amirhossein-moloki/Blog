from django.contrib.auth import get_user_model
from django.test import TestCase

from posts.factories import AuthorProfileFactory, CategoryFactory, ArticleFactory
from posts.models import Article, ArticleTranslation

User = get_user_model()


class ArticleModelTests(TestCase):
    def test_article_reading_time_calculation(self):
        # 200 words should be around 1 minute (60 seconds)
        content = "word " * 200
        author = AuthorProfileFactory()
        article = Article.objects.create(author=author)
        pt = ArticleTranslation.objects.create(
            article=article,
            language_code="en",
            title="Test Article",
            slug="test-article",
            content=content,
            excerpt="Excerpt",
        )
        self.assertEqual(pt.reading_time_sec, 60)

    def test_article_reading_time_empty_content(self):
        author = AuthorProfileFactory()
        article = Article.objects.create(author=author)
        pt = ArticleTranslation.objects.create(
            article=article,
            language_code="en",
            title="Test Article",
            slug="test-article-empty",
            content="",
            excerpt="Excerpt",
        )
        self.assertEqual(pt.reading_time_sec, 0)

    def test_article_str(self):
        article = ArticleFactory(translation__title="Unique Title")
        self.assertEqual(str(article.translation), "Unique Title (en)")


class AuthorProfileModelTests(TestCase):
    def test_author_profile_str(self):
        author = AuthorProfileFactory(display_name="John Doe")
        self.assertEqual(str(author), "John Doe")


class CategoryModelTests(TestCase):
    def test_category_str(self):
        category = CategoryFactory(name="Tech")
        self.assertEqual(str(category), "Tech")
