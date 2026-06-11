from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rest_framework import status

from interactions.models import Comment
from posts.blog_tests.base import BaseAPITestCase
from posts.factories import CommentFactory, PostFactory, RevisionFactory
from posts.models import Post


class RevisionAPITest(BaseAPITestCase):
    def test_list_revisions_for_post(self):
        post = PostFactory()
        RevisionFactory.create_batch(3, post=post)
        url = reverse("posts:revision-list") + f"?post={post.pk}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)


class ReactionAPITest(BaseAPITestCase):
    def test_create_reaction_for_post(self):
        self._authenticate()
        post = PostFactory()
        url = reverse("interactions:reaction-list")
        content_type = ContentType.objects.get_for_model(Post)
        data = {
            "content_type": content_type.pk,
            "object_id": post.pk,
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
