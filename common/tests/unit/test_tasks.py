import os
from unittest.mock import MagicMock, patch

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import TestCase

from common.tasks import convert_image_to_avif_task
from posts.factories import PostFactory


class TasksTest(TestCase):
    def setUp(self):
        # Create a post with an image
        self.post = PostFactory()
        self.post.image.save(
            "test_image.jpg", ContentFile(b"test image content"), save=True
        )

    def test_convert_image_to_avif_task_success(self):
        # Mock convert_image_to_avif to return a ContentFile
        mock_avif_file = ContentFile(b"fake avif content", name="test_image.avif")

        with patch("common.tasks.convert_image_to_avif", return_value=mock_avif_file):
            with patch("common.tasks.get_sanitized_filename", side_effect=lambda x: x):
                result = convert_image_to_avif_task(
                    "posts", "Post", self.post.pk, "image"
                )

        self.assertIn("Successfully converted image", result)
        self.post.refresh_from_db()
        self.assertTrue(self.post.image.name.endswith(".avif"))

    def test_convert_image_to_avif_task_no_action(self):
        # Already an avif
        self.post.image.name = "already.avif"
        self.post.save()

        result = convert_image_to_avif_task("posts", "Post", self.post.pk, "image")
        self.assertIn("No action needed", result)

    def test_convert_image_to_avif_task_instance_not_found(self):
        result = convert_image_to_avif_task("posts", "Post", 99999, "image")
        self.assertIn("not found. Skipping", result)
