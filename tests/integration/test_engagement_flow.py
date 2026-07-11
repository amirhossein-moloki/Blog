from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rest_framework import status

from interactions.models import Comment, Reaction
from posts.blog_tests.base import BaseAPITestCase
from posts.factories import ArticleFactory, CommentFactory


class EngagementFlowIntegrationTest(BaseAPITestCase):
    @patch("interactions.views.notify_author_on_new_comment.delay")
    def test_commenting_and_reply_flow(self, mock_notify):
        self._authenticate()
        article = ArticleFactory()

        # 1. Post a comment
        url = reverse("interactions:comment-list")
        comment_data = {"article": article.id, "content": "Great article!"}
        response = self.client.post(url, comment_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        if "data" in response.data:
            comment_id = response.data["data"]["id"]
        else:
            comment_id = response.data["id"]

        self.assertTrue(
            Comment.objects.filter(
                id=comment_id, user=self.user, article=article
            ).exists()
        )

        # Verify notification task was called
        mock_notify.assert_called_once()

        # 2. Reply to the comment
        reply_data = {
            "article": article.id,
            "content": "I agree!",
            "parent": comment_id,
        }
        response = self.client.post(url, reply_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        if "data" in response.data:
            reply_id = response.data["data"]["id"]
        else:
            reply_id = response.data["id"]

        self.assertTrue(
            Comment.objects.filter(id=reply_id, parent_id=comment_id).exists()
        )

    def test_reaction_on_article(self):
        self._authenticate()
        article = ArticleFactory()
        url = reverse("interactions:reaction-list")

        content_type = ContentType.objects.get_for_model(article)
        reaction_data = {
            "content_type": content_type.id,
            "object_id": article.id,
            "reaction": "like",
        }

        # 1. Add reaction
        response = self.client.post(url, reaction_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Reaction.objects.filter(
                user=self.user, object_id=article.id, reaction="like"
            ).exists()
        )

        # 2. Attempting to add the same reaction
        response = self.client.post(url, reaction_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reaction_on_comment(self):
        self._authenticate()
        comment = CommentFactory()
        url = reverse("interactions:reaction-list")

        content_type = ContentType.objects.get_for_model(comment)
        reaction_data = {
            "content_type": content_type.id,
            "object_id": comment.id,
            "reaction": "like",
        }

        response = self.client.post(url, reaction_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Reaction.objects.filter(
                user=self.user, content_type=content_type, object_id=comment.id
            ).exists()
        )
