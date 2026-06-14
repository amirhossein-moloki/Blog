from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from medias.services import create_media_from_file
from posts.factories import UserFactory


class MediaServicesTest(TestCase):
    @patch("medias.services.default_storage.save")
    @patch("medias.services.default_storage.url")
    @patch("medias.services.Image.open")
    def test_create_media_from_file_image(self, mock_image_open, mock_url, mock_save):
        user = UserFactory()
        mock_file = SimpleUploadedFile(
            "test.jpg", b"content", content_type="image/jpeg"
        )
        mock_save.return_value = "test.jpg"
        mock_url.return_value = "http://example.com/test.jpg"

        mock_img = MagicMock()
        mock_img.width = 100
        mock_img.height = 200
        mock_image_open.return_value.__enter__.return_value = mock_img

        media = create_media_from_file(mock_file, user)
        self.assertEqual(media.type, "image")
