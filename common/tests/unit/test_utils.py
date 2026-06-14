from django.test import TestCase

from common.utils.files import get_sanitized_filename, get_sanitized_upload_path


class UtilsTest(TestCase):
    def test_get_sanitized_filename(self):
        self.assertEqual(get_sanitized_filename("test file.jpg"), "test-file.jpg")
        self.assertEqual(get_sanitized_filename("file (1).png"), "file-1.png")

    def test_get_sanitized_upload_path(self):
        path = get_sanitized_upload_path(None, "test.jpg")
        self.assertTrue(path.startswith("uploads/"))
        self.assertTrue(path.endswith(".jpg"))
