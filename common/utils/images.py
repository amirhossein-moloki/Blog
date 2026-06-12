# common/utils/images.py

import os
from io import BytesIO

import pillow_avif  # noqa: F401 -> Registered plugin
from django.core.files.base import ContentFile
from PIL import Image

from .files import get_sanitized_filename


def convert_image_to_avif(image_field, max_dimension=1920, quality=50, speed=6):
    """
    Input: An ImageField/File
    Output: A ContentFile in AVIF format, ready to be saved in an ImageField
    """
    # Move the file pointer to the beginning of the file
    image_field.seek(0)

    # Open the file with Pillow
    img = Image.open(image_field)

    # Extract the color profile to add to the new image later
    icc_profile = img.info.get("icc_profile")

    # To preserve transparency, we do not convert images with RGBA mode.
    # Other modes like CMYK or P are converted to RGBA to preserve potential transparency.
    if img.mode not in ("RGB", "L", "RGBA"):
        img = img.convert("RGBA")

    # If the width or height of the image is too large, resize it
    if img.width > max_dimension or img.height > max_dimension:
        img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

    # Save in AVIF format in the buffer
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

    # Change the file extension to .avif
    original_name = getattr(image_field, "name", "untitled.avif")
    sanitized_name = get_sanitized_filename(original_name)

    # Ensure the final name has a .avif extension
    base_name, _ = os.path.splitext(sanitized_name)
    new_name = f"{base_name}.avif"

    return ContentFile(buffer.read(), name=new_name)
