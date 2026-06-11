import io

from django.test import TestCase
from PIL import Image

from common.utils.files import get_sanitized_filename, get_sanitized_upload_path
from common.utils.images import convert_image_to_avif


class UtilsTest(TestCase):
    def test_get_sanitized_filename(self):
        self.assertEqual(get_sanitized_filename("test file.jpg"), "test-file.jpg")
        self.assertEqual(get_sanitized_filename("file (1).png"), "file-1.png")

    def test_get_sanitized_upload_path(self):
        path = get_sanitized_upload_path(None, "test.jpg")
        self.assertTrue(path.startswith("uploads/"))
        self.assertTrue(path.endswith(".jpg"))

    def test_convert_image_to_avif(self):
        file = io.BytesIO()
        # Test non-standard mode conversion
        image = Image.new("P", size=(100, 100))
        image.save(file, "png")
        file.name = "test.png"
        file.seek(0)

        result = convert_image_to_avif(file)
        self.assertTrue(result.name.endswith(".avif"))
        self.assertTrue(len(result.read()) > 0)

    def test_convert_image_to_avif_resize(self):
        file = io.BytesIO()
        image = Image.new("RGB", size=(2000, 1000))
        image.save(file, "png")
        file.name = "large.png"
        file.seek(0)

        result = convert_image_to_avif(file, max_dimension=1000)
        result_img = Image.open(result)
        self.assertEqual(result_img.width, 1000)
        self.assertEqual(result_img.height, 500)

    def test_convert_image_to_avif_with_icc(self):
        file = io.BytesIO()
        image = Image.new("RGB", size=(10, 10))
        image.save(file, "png", icc_profile=b"fake_icc")
        file.name = "icc.png"
        file.seek(0)

        result = convert_image_to_avif(file)
        self.assertTrue(result.name.endswith(".avif"))
