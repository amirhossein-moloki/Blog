from django.test import TestCase
from common.utils.files import get_sanitized_filename
class UtilsTest(TestCase):
    def test_get_sanitized_filename(self):
        self.assertEqual(get_sanitized_filename("test file.jpg"), "test-file.jpg")
