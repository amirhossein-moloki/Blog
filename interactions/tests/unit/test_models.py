from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from interactions.models import Comment, Reaction
from posts.factories import CommentFactory, ArticleFactory, UserFactory


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
        CommentFactory(parent=parent, article=parent.article)
        self.assertEqual(parent.replies.count(), 1)


class ReactionModelTest(TestCase):
    def test_reaction_creation(self):
        article = ArticleFactory()
        user = UserFactory()
        ct = ContentType.objects.get_for_model(article)
        reaction = Reaction.objects.create(
            user=user, content_type=ct, object_id=article.id, reaction="like"
        )
        self.assertEqual(reaction.reaction, "like")
