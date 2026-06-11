from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from interactions.models import Comment, Reaction
from posts.factories import CommentFactory, PostFactory, UserFactory


class CommentModelTest(TestCase):
    def test_comment_creation(self):
        comment = CommentFactory()
        self.assertIsInstance(comment, Comment)
        self.assertEqual(comment.status, "approved")

    def test_comment_str(self):
        comment = CommentFactory()
        self.assertIn(str(comment.user), str(comment))

    def test_comment_replies(self):
        parent = CommentFactory()
        CommentFactory(parent=parent, post=parent.post)
        self.assertEqual(parent.replies.count(), 1)


class ReactionModelTest(TestCase):
    def test_reaction_creation(self):
        post = PostFactory()
        user = UserFactory()
        ct = ContentType.objects.get_for_model(post)
        reaction = Reaction.objects.create(
            user=user, content_type=ct, object_id=post.id, reaction="like"
        )
        self.assertEqual(reaction.reaction, "like")
