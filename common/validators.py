import re

from django.core.exceptions import ValidationError


def validate_file(value):
    """
    Validates file size and type.
    """
    filesize = value.size
    if filesize > 10 * 1024 * 1024:
        raise ValidationError(
            "Your file size is greater than 10 MB. Please upload a smaller file."
        )

    allowed_extensions = [
        ".jpg",
        ".jpeg",
        ".png",
        ".mp4",
        ".mov",
        ".webp",
        ".gif",
        ".heic",
        ".avif",
    ]
    ext = str(value).split(".")[-1].lower()
    if f".{ext}" not in allowed_extensions:
        raise ValidationError(
            f"The file format '.{ext}' is not supported. Please try one of the allowed formats: {', '.join(allowed_extensions)}"
        )


def validate_sheba(value):
    """
    Validates a SHEBA number.
    A valid SHEBA number starts with 'IR' followed by 24 digits.
    """
    if not re.match(r"^IR\d{24}$", value):
        raise ValidationError(
            "Invalid SHEBA number. It must start with IR and contain 24 digits."
        )


def validate_card_number(value):
    """
    Validates a bank card number.
    A valid card number is a 16-digit number.
    This is a basic check and does not perform checksum validation.
    """
    if not re.match(r"^\d{16}$", value):
        raise ValidationError("Invalid card number. It must be 16 digits.")
