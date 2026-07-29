from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.test import TestCase

from medias.models import Media, MediaVariant
from medias.services import (
    create_media_from_file,
    validate_file_security,
    MalwareScanner,
    MediaUsageService,
    MediaDeletionService,
)
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

    def test_validate_file_security_valid_jpeg(self):
        # 1. Test Valid JPEG header with real JPEG signature
        valid_jpeg_data = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00..."
        uploaded_file = SimpleUploadedFile(
            "valid.jpg", valid_jpeg_data, content_type="image/jpeg"
        )
        mime = validate_file_security(uploaded_file)
        self.assertEqual(mime, "image/jpeg")

    def test_validate_file_security_invalid_extension(self):
        uploaded_file = SimpleUploadedFile(
            "malicious.sh", b"#!/bin/bash\necho 1", content_type="text/plain"
        )
        with self.assertRaises(ValidationError) as ctx:
            validate_file_security(uploaded_file)
        self.assertIn("extension", str(ctx.exception))

    def test_validate_file_security_malicious_script(self):
        uploaded_file = SimpleUploadedFile(
            "fake.jpg", b"<?php phpinfo(); ?>", content_type="image/jpeg"
        )
        with self.assertRaises(ValidationError) as ctx:
            validate_file_security(uploaded_file)
        self.assertIn("forbidden scripts", str(ctx.exception))

    def test_validate_file_security_malware_quarantine(self):
        # EICAR signature triggers MalwareScanner rejection
        malware_data = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
        uploaded_file = SimpleUploadedFile(
            "infected.jpg", malware_data, content_type="image/jpeg"
        )
        with self.assertRaises(ValidationError) as ctx:
            validate_file_security(uploaded_file)
        self.assertIn("quarantined", str(ctx.exception))

    def test_duplicate_detection_prevents_reupload(self):
        user = UserFactory()
        jpeg_data = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00_some_unique_content_here..."

        file1 = SimpleUploadedFile("image1.jpg", jpeg_data, content_type="image/jpeg")
        media1 = create_media_from_file(file1, user)

        file2 = SimpleUploadedFile("image2.jpg", jpeg_data, content_type="image/jpeg")
        media2 = create_media_from_file(file2, user)

        # Second upload should be identified as duplicate
        self.assertTrue(getattr(media2, "is_duplicate", False))
        self.assertEqual(media2.id, media1.id)

    def test_media_lifecycle_soft_delete_and_restore(self):
        user = UserFactory()
        jpeg_data = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00_lifecycle..."
        uploaded_file = SimpleUploadedFile("lifecycle.jpg", jpeg_data, content_type="image/jpeg")
        media = create_media_from_file(uploaded_file, user)

        # Soft delete
        MediaDeletionService.soft_delete(media)
        media.refresh_from_db()
        self.assertTrue(media.is_deleted)
        self.assertFalse(media.is_active)

        # Restore
        MediaDeletionService.restore(media)
        media.refresh_from_db()
        self.assertFalse(media.is_deleted)
        self.assertTrue(media.is_active)
