# common/utils/images.py

import os
from io import BytesIO

import pillow_avif  # noqa: F401 -> Registered plugin
from django.core.files.base import ContentFile
from PIL import Image

from .files import get_sanitized_filename


def convert_image_to_avif(image_field, max_dimension=1920, quality=50, speed=6):
    """
    EN:
    Converts a Django ImageField or file-like object to AVIF format.
    Handles resizing, mode conversion, and ICC profile preservation.

    FA:
    تبدیل یک ImageField جنگو یا شیء شبیه فایل به فرمت AVIF.
    مدیریت تغییر اندازه، تغییر حالت (mode) و حفظ پروفایل ICC.

    Args:
        image_field: Input image field or file.
        max_dimension (int): Maximum width or height for resizing.
        quality (int): Compression quality (0-100).
        speed (int): Encoding speed (0-10).

    Returns:
        ContentFile: The converted image as a Django ContentFile.
    """
    # EN: Move the file pointer to the beginning of the file
    # FA: انتقال نشانگر فایل به ابتدای فایل
    image_field.seek(0)

    # EN: Open the file with Pillow
    # FA: باز کردن فایل با Pillow
    img = Image.open(image_field)

    # EN: Extract the color profile to add to the new image later
    # FA: استخراج پروفایل رنگ برای اضافه کردن به تصویر جدید در مراحل بعد
    icc_profile = img.info.get("icc_profile")

    # EN: To preserve transparency, we do not convert images with RGBA mode.
    # EN: Other modes like CMYK or P are converted to RGBA to preserve potential transparency.
    # FA: برای حفظ شفافیت، تصاویر با حالت RGBA را تبدیل نمی‌کنیم.
    # FA: حالت‌های دیگر مانند CMYK یا P برای حفظ شفافیت احتمالی به RGBA تبدیل می‌شوند.
    if img.mode not in ("RGB", "L", "RGBA"):
        img = img.convert("RGBA")

    # EN: If the width or height of the image is too large, resize it
    # FA: اگر عرض یا ارتفاع تصویر خیلی بزرگ باشد، اندازه آن را تغییر دهید
    if img.width > max_dimension or img.height > max_dimension:
        img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

    # EN: Save in AVIF format in the buffer
    # FA: ذخیره با فرمت AVIF در بافر
    buffer = BytesIO()
    save_kwargs = {
        "format": "AVIF",
        "quality": quality,
        "speed": speed,
        "strip": True,
    }
    if icc_profile:
        save_kwargs["icc_profile"] = icc_profile

    img.save(buffer, **save_kwargs)
    buffer.seek(0)

    # EN: Change the file extension to .avif
    # FA: تغییر پسوند فایل به .avif
    original_name = getattr(image_field, "name", "untitled.avif")
    sanitized_name = get_sanitized_filename(original_name)

    # EN: Ensure the final name has a .avif extension
    # FA: اطمینان از اینکه نام نهایی دارای پسوند .avif باشد
    base_name, _ = os.path.splitext(sanitized_name)
    new_name = f"{base_name}.avif"

    return ContentFile(buffer.read(), name=new_name)
