from celery import shared_task
from django.apps import apps
from django.core.files.storage import default_storage

from .utils.files import get_sanitized_filename
from .utils.images import convert_image_to_avif


@shared_task(bind=True, max_retries=3)
def convert_image_to_avif_task(
    self, app_label, model_name, instance_pk, field_name, quality=50, speed=6
):
    """
    EN:
    A Celery task for asynchronously converting an image field to AVIF format.
    This task helps in reducing image size for better performance without blocking the main thread.

    FA:
    یک تسک Celery برای تبدیل نامتقارن یک فیلد تصویر به فرمت AVIF.
    این تسک به کاهش حجم تصاویر برای کارایی بهتر بدون مسدود کردن ترد اصلی کمک می‌کند.

    Args:
        app_label (str): Name of the Django app.
        model_name (str): Name of the model.
        instance_pk (int/str): Primary key of the model instance.
        field_name (str): Name of the image field to convert.
        quality (int): Compression quality (0-100).
        speed (int): Encoding speed (0-10).
    """
    try:
        # EN: Find the model and object from the database
        # FA: یافتن مدل و شیء از پایگاه داده
        Model = apps.get_model(app_label, model_name)
        instance = Model.objects.get(pk=instance_pk)

        image_field = getattr(instance, field_name)

        # EN: If no file exists or it's already AVIF, do nothing
        # FA: اگر فایلی وجود ندارد یا قبلاً AVIF است، کاری انجام ندهید
        if (
            not image_field
            or not image_field.name
            or image_field.name.lower().endswith(".avif")
        ):
            return f"No action needed for {model_name} {instance_pk}."

        original_name = image_field.name

        # EN: 1. Convert the image to AVIF in memory. The utility returns a ContentFile.
        # FA: ۱. تبدیل تصویر به AVIF در حافظه. ابزار کمکی یک ContentFile بازمی‌گرداند.
        avif_content_file = convert_image_to_avif(
            image_field, quality=quality, speed=speed
        )

        # EN: 2. Sanitize the filename and save the new file to storage.
        # FA: ۲. پاکسازی نام فایل و ذخیره فایل جدید در فضای ذخیره‌سازی.
        sanitized_name = get_sanitized_filename(avif_content_file.name)
        saved_name = default_storage.save(sanitized_name, avif_content_file)

        # EN: 4. Update the model
        # FA: ۴. به‌روزرسانی مدل
        setattr(instance, field_name, saved_name)
        instance.save(update_fields=[field_name])

        # EN: 5. Delete the original file (if different)
        # FA: ۵. حذف فایل اصلی (اگر متفاوت باشد)
        if saved_name != original_name and default_storage.exists(original_name):
            default_storage.delete(original_name)

        return f"Successfully converted image for {model_name} {instance_pk}."

    except Model.DoesNotExist:
        # EN: If the object was deleted before the task executed, it's fine
        # FA: اگر شیء قبل از اجرای تسک حذف شده باشد، مشکلی نیست
        return f"{model_name} with pk {instance_pk} not found. Skipping."
    except Exception as exc:
        # EN: If an error occurs, Celery retries the task (up to 3 times)
        # FA: در صورت بروز خطا، Celery تسک را دوباره امتحان می‌کند (تا ۳ بار)
        raise self.retry(exc=exc, countdown=60)  # Retry after 60 seconds
