from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rest_framework import status

from interactions.models import Comment
from posts.blog_tests.base import BaseAPITestCase
from posts.factories import ArticleFactory, CommentFactory, RevisionFactory
from posts.models import Article


class RevisionAPITest(BaseAPITestCase):
    def test_list_revisions_for_article(self):
        article = ArticleFactory()
        RevisionFactory.create_batch(3, article=article)
        url = reverse("posts:revision-list") + f"?article={article.pk}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)


class ReactionAPITest(BaseAPITestCase):
    def test_create_reaction_for_article(self):
        self._authenticate()
        article = ArticleFactory()
        url = reverse("interactions:reaction-list")
        content_type = ContentType.objects.get_for_model(Article)
        data = {
            "content_type": content_type.pk,
            "object_id": article.pk,
            "reaction": "like",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_reaction_for_comment(self):
        self._authenticate()
        comment = CommentFactory()
        url = reverse("interactions:reaction-list")
        content_type = ContentType.objects.get_for_model(Comment)
        data = {
            "content_type": content_type.pk,
            "object_id": comment.pk,
            "reaction": "thumbs_up",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
