from django.test import TestCase
from unittest.mock import patch, MagicMock
from django.core.files.uploadedfile import SimpleUploadedFile
from posts.factories import UserFactory
from medias.services import create_media_from_file

class MediaServicesTest(TestCase):
    @patch('medias.services.default_storage.save')
    @patch('medias.services.default_storage.url')
    @patch('medias.services.convert_image_to_avif')
    @patch('medias.services.Image.open')
    def test_create_media_from_file_image(self, mock_image_open, mock_convert, mock_url, mock_save):
        user = UserFactory()
        mock_file = SimpleUploadedFile("test.jpg", b"content", content_type="image/jpeg")
        mock_convert.return_value = mock_file
        mock_save.return_value = 'test.avif'
        mock_url.return_value = 'http://example.com/test.avif'

        mock_img = MagicMock()
        mock_img.width = 100
        mock_img.height = 200
        mock_image_open.return_value.__enter__.return_value = mock_img

        media = create_media_from_file(mock_file, user)
        self.assertEqual(media.type, 'image')
