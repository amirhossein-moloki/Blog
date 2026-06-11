from unittest.mock import patch

from django.test import TestCase

from interactions.models import Comment, Reaction
from interactions.services import create_comment, toggle_reaction
from posts.factories import PostFactory, UserFactory


class InteractionServicesTest(TestCase):
    @patch("interactions.services.notify_author_on_new_comment.delay")
    def test_create_comment_service(self, mock_notify):
        user = UserFactory()
        post = PostFactory()
        create_comment(user=user, post=post, content="Test content")
        self.assertEqual(Comment.objects.count(), 1)
        mock_notify.assert_called_once()

    def test_toggle_reaction(self):
        user = UserFactory()
        post = PostFactory()
        reaction = toggle_reaction(user, post, "like")
        self.assertIsNotNone(reaction)
        self.assertEqual(Reaction.objects.count(), 1)

        toggle_reaction(user, post, "like")
        self.assertEqual(Reaction.objects.count(), 0)
