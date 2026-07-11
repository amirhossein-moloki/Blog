from unittest.mock import patch

from django.test import TestCase

from posts.tasks import (
    increment_article_view_count_task,
    publish_scheduled_articles_task,
)


class ArticleTaskTests(TestCase):
    @patch("posts.tasks.increment_article_view_count")
    def test_increment_article_view_count_task(self, mock_service):
        increment_article_view_count_task(1)
        mock_service.assert_called_once_with(1)

    @patch("posts.tasks.publish_scheduled_articles")
    def test_publish_scheduled_articles_task(self, mock_service):
        publish_scheduled_articles_task()
        mock_service.assert_called_once()
