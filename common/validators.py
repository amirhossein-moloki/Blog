import re

from django.core.exceptions import ValidationError


def validate_file(value):
    """
    EN:
    Validates the size and type of an uploaded file.
    Limits file size to 10MB and checks against a list of allowed extensions.

    FA:
    اعتبارسنجی اندازه و نوع فایل آپلود شده.
    اندازه فایل را به ۱۰ مگابایت محدود کرده و پسوند آن را با لیست پسوندهای مجاز بررسی می‌کند.
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
    EN:
    Validates an Iranian SHEBA (IBAN) number.
    A valid SHEBA number starts with 'IR' followed by 24 digits.

    FA:
    اعتبارسنجی شماره شبا.
    یک شماره شبای معتبر با 'IR' شروع شده و با ۲۴ رقم ادامه می‌یابد.
    """
    if not re.match(r"^IR\d{24}$", value):
        raise ValidationError(
            "Invalid SHEBA number. It must start with IR and contain 24 digits."
        )


def validate_card_number(value):
    """
    EN:
    Validates a bank card number.
    Checks if the input is a 16-digit string.

    FA:
    اعتبارسنجی شماره کارت بانکی.
    بررسی می‌کند که ورودی یک رشته ۱۶ رقمی باشد.
    """
    if not re.match(r"^\d{16}$", value):
        raise ValidationError("Invalid card number. It must be 16 digits.")
