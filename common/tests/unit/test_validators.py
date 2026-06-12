from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from common.validators import validate_card_number, validate_file, validate_sheba


class ValidatorTests(TestCase):
    def test_validate_file_valid(self):
        small_file = SimpleUploadedFile(
            "test.jpg", b"file_content", content_type="image/jpeg"
        )
        try:
            validate_file(small_file)
        except ValidationError:
            self.fail("validate_file raised ValidationError unexpectedly!")

    def test_validate_file_too_large(self):
        large_file = SimpleUploadedFile(
            "test.jpg", b"a" * (10 * 1024 * 1024 + 1), content_type="image/jpeg"
        )
        with self.assertRaises(ValidationError) as cm:
            validate_file(large_file)
        self.assertIn("greater than 10 MB", str(cm.exception))

    def test_validate_file_invalid_extension(self):
        invalid_file = SimpleUploadedFile(
            "test.txt", b"file_content", content_type="text/plain"
        )
        with self.assertRaises(ValidationError) as cm:
            validate_file(invalid_file)
        # Check for the presence of the extension in the error message
        self.assertIn(".txt", str(cm.exception))

    def test_validate_sheba_valid(self):
        valid_sheba = "IR" + "1" * 24
        try:
            validate_sheba(valid_sheba)
        except ValidationError:
            self.fail("validate_sheba raised ValidationError unexpectedly!")

    def test_validate_sheba_invalid_format(self):
        invalid_sheba = "US" + "1" * 24
        with self.assertRaises(ValidationError):
            validate_sheba(invalid_sheba)

        too_short_sheba = "IR" + "1" * 23
        with self.assertRaises(ValidationError):
            validate_sheba(too_short_sheba)

    def test_validate_card_number_valid(self):
        valid_card = "1" * 16
        try:
            validate_card_number(valid_card)
        except ValidationError:
            self.fail("validate_card_number raised ValidationError unexpectedly!")

    def test_validate_card_number_invalid(self):
        invalid_card = "1" * 15
        with self.assertRaises(ValidationError):
            validate_card_number(invalid_card)

        non_digit_card = "a" * 16
        with self.assertRaises(ValidationError):
            validate_card_number(non_digit_card)
