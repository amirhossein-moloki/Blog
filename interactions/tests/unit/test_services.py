from django.test import TestCase

from interactions.models import Comment, Reaction
from interactions.services import create_comment, toggle_reaction
from posts.factories import PostFactory, UserFactory


class InteractionServicesTest(TestCase):
    def test_create_comment_service(self):
        user = UserFactory()
        post = PostFactory()
        create_comment(user=user, post=post, content="Test content")
        self.assertEqual(Comment.objects.count(), 1)

    def test_toggle_reaction(self):
        user = UserFactory()
        post = PostFactory()
        reaction = toggle_reaction(user, post, "like")
        self.assertIsNotNone(reaction)
        self.assertEqual(Reaction.objects.count(), 1)

        toggle_reaction(user, post, "like")
        self.assertEqual(Reaction.objects.count(), 0)
