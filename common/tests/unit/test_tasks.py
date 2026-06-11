import os
from unittest.mock import MagicMock, patch

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import TestCase

from common.tasks import convert_image_to_avif_task
from posts.factories import UserFactory


class TasksTest(TestCase):
    def setUp(self):
        # Create a user with a profile picture
        self.user = UserFactory()
        self.user.profile_picture.save(
            "test_image.jpg", ContentFile(b"test image content"), save=True
        )

    def test_convert_image_to_avif_task_success(self):
        # Mock convert_image_to_avif to return a ContentFile
        mock_avif_file = ContentFile(b"fake avif content", name="test_image.avif")

        with patch("common.tasks.convert_image_to_avif", return_value=mock_avif_file):
            with patch("common.tasks.get_sanitized_filename", side_effect=lambda x: x):
                result = convert_image_to_avif_task(
                    "users", "User", self.user.pk, "profile_picture"
                )

        self.assertIn("Successfully converted image", result)
        self.user.refresh_from_db()
        self.assertTrue(self.user.profile_picture.name.endswith(".avif"))

    def test_convert_image_to_avif_task_no_action(self):
        # Already an avif
        self.user.profile_picture.name = "already.avif"
        self.user.save()

        result = convert_image_to_avif_task(
            "users", "User", self.user.pk, "profile_picture"
        )
        self.assertIn("No action needed", result)

    def test_convert_image_to_avif_task_instance_not_found(self):
        result = convert_image_to_avif_task("users", "User", 99999, "profile_picture")
        self.assertIn("not found. Skipping", result)
