import os
from django.test import TestCase
from django.core.files.base import ContentFile
from common.utils.files import get_sanitized_filename, get_sanitized_upload_path
from common.utils.images import convert_image_to_avif
from common.optimization import optimize_image
from PIL import Image
from io import BytesIO

class FileUtilsTests(TestCase):
    def test_get_sanitized_filename(self):
        self.assertEqual(get_sanitized_filename("Hello World.jpg"), "hello-world.jpg")
        self.assertEqual(get_sanitized_filename("test!@#.png"), "test.png")

    def test_get_sanitized_upload_path(self):
        path = get_sanitized_upload_path(None, "test.jpg")
        self.assertTrue(path.startswith("uploads/"))
        self.assertTrue(path.endswith(".jpg"))
        # Check if it has a UUID (length check is a simple proxy)
        self.assertGreater(len(path), 20)

class ImageUtilsTests(TestCase):
    def test_convert_image_to_avif(self):
        # Create a simple RGB image
        img = Image.new('RGB', (100, 100), color='red')
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)

        image_field = ContentFile(img_io.read(), name="test.jpg")

        avif_file = convert_image_to_avif(image_field)

        self.assertTrue(avif_file.name.endswith(".avif"))
        # Verify it's a valid image (AVIF)
        avif_img = Image.open(avif_file)
        self.assertEqual(avif_img.format, "AVIF")

    def test_convert_image_to_avif_resizing(self):
        # Create a large image
        img = Image.new('RGB', (2000, 1000), color='blue')
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)

        image_field = ContentFile(img_io.read(), name="large.jpg")

        avif_file = convert_image_to_avif(image_field, max_dimension=1000)

        avif_img = Image.open(avif_file)
        self.assertLessEqual(avif_img.width, 1000)
        self.assertLessEqual(avif_img.height, 1000)

class OptimizationTests(TestCase):
    def test_optimize_image(self):
        img = Image.new('RGB', (100, 100), color='green')
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)

        image_field = ContentFile(img_io.read(), name="green.jpg")

        result = optimize_image(image_field)

        self.assertIsNotNone(result)
        self.assertTrue(result['filename'].endswith('.avif'))
        self.assertIsInstance(result['buffer'], BytesIO)

    def test_optimize_image_rgba(self):
        img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
        img_io = BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)

        image_field = ContentFile(img_io.read(), name="red_alpha.png")

        result = optimize_image(image_field)

        self.assertIsNotNone(result)
        self.assertTrue(result['filename'].endswith('.avif'))

    def test_optimize_image_failure(self):
        # Invalid image content
        image_field = ContentFile(b"not an image", name="bad.jpg")
        result = optimize_image(image_field)
        self.assertIsNone(result)
