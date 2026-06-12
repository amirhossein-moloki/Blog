from django.core.files.storage import default_storage
from PIL import Image

from common.utils.files import get_sanitized_filename
from common.utils.images import convert_image_to_avif

from .models import Media


def create_media_from_file(uploaded_file, uploaded_by, alt_text="", title=""):
    """
    EN:
    Service to handle media file creation.
    Performs image optimization (AVIF conversion), sanitizes filenames,
    and extracts metadata (width, height, type).

    FA:
    سرویسی برای مدیریت ایجاد فایل‌های رسانه‌ای.
    بهینه‌سازی تصویر (تبدیل به AVIF)، پاکسازی نام فایل و استخراج متادیتا (عرض، ارتفاع، نوع) را انجام می‌دهد.

    Args:
        uploaded_file (File): The file being uploaded.
        uploaded_by (User): The user who uploaded the file.
        alt_text (str): Alternative text for images.
        title (str): Title for the media file.

    Returns:
        Media: The created Media instance.
    """
    original_content_type = uploaded_file.content_type
    is_image = "image" in original_content_type

    if is_image:
        # EN: Convert images to AVIF for better performance
        # FA: تبدیل تصاویر به AVIF برای کارایی بهتر
        processed_file = convert_image_to_avif(uploaded_file)
        mime = "image/avif"
    else:
        processed_file = uploaded_file
        mime = original_content_type

    sanitized_name = get_sanitized_filename(processed_file.name)
    storage_key = default_storage.save(sanitized_name, processed_file)
    file_url = default_storage.url(storage_key)

    if not title:
        title = sanitized_name

    media_data = {
        "storage_key": storage_key,
        "url": file_url,
        "size_bytes": processed_file.size,
        "mime": mime,
        "title": title,
        "alt_text": alt_text,
        "uploaded_by": uploaded_by,
    }

    if is_image:
        media_data["type"] = "image"
        try:
            processed_file.seek(0)
            with Image.open(processed_file) as img:
                media_data["width"] = img.width
                media_data["height"] = img.height
        except Exception:
            media_data["width"] = None
            media_data["height"] = None
    elif "video" in original_content_type:
        media_data["type"] = "video"
    else:
        media_data["type"] = "file"

    return Media.objects.create(**media_data)
