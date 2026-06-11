from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from interactions.models import Comment, Reaction
from posts.models import AuthorProfile, Post
from users.models import User


class InteractionsViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="interact", password="password")
        self.admin = User.objects.create_superuser(
            username="admin", password="password", email="admin@example.com"
        )
        self.author_profile = AuthorProfile.objects.create(
            user=self.admin, display_name="Admin Author"
        )
        self.post = Post.objects.create(
            title="Post", slug="post", author=self.author_profile, status="published"
        )
        self.comment = Comment.objects.create(
            post=self.post, user=self.user, content="Comment", status="approved"
        )
        self.comment_pending = Comment.objects.create(
            post=self.post, user=self.user, content="Pending", status="pending"
        )
        self.comment_url = reverse("interactions:comment-list")
        self.reaction_url = reverse("interactions:reaction-list")

    def test_comment_queryset_staff(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.comment_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"] if "data" in response.data else response.data
        self.assertEqual(len(data), 2)

    def test_comment_queryset_regular(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.comment_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"] if "data" in response.data else response.data
        self.assertEqual(len(data), 1)

    @patch("interactions.views.notify_author_on_new_comment.delay")
    def test_comment_create_mocks_celery(self, mock_notify):
        self.client.force_authenticate(user=self.user)
        data = {"post": self.post.id, "content": "New Comment"}
        response = self.client.post(self.comment_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_notify.assert_called_once()

    def test_reaction_queryset_staff(self):
        ct = ContentType.objects.get_for_model(Post)
        Reaction.objects.create(
            user=self.user, content_type=ct, object_id=self.post.id, reaction="like"
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.reaction_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"] if "data" in response.data else response.data
        self.assertEqual(len(data), 1)

    def test_reaction_queryset_regular(self):
        other_user = User.objects.create_user(username="other3", password="password")
        ct = ContentType.objects.get_for_model(Post)
        Reaction.objects.create(
            user=self.user, content_type=ct, object_id=self.post.id, reaction="like"
        )
        Reaction.objects.create(
            user=other_user, content_type=ct, object_id=self.post.id, reaction="like"
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.reaction_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"] if "data" in response.data else response.data
        self.assertEqual(len(data), 1)
