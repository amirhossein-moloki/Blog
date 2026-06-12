import os
import uuid

from django.utils.text import slugify


def get_sanitized_filename(filename):
    """
    EN:
    Generates a sanitized filename by slugifying the base name and preserving the extension.

    FA:
    تولید یک نام فایل پاکسازی شده با تبدیل نام اصلی به اسلاگ و حفظ پسوند.
    """
    base, ext = os.path.splitext(filename)
    return f"{slugify(base)}{ext}"


def get_sanitized_upload_path(instance, filename):
    """
    EN:
    Generates a unique upload path using a UUID and a sanitized filename.
    Useful for preventing filename collisions and securing file access.

    FA:
    تولید یک مسیر آپلود منحصر به فرد با استفاده از UUID و نام فایل پاکسازی شده.
    مفید برای جلوگیری از تداخل نام فایل‌ها و امنیت دسترسی به فایل.
    """
    ext = filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join("uploads", filename)
