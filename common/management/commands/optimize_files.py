import os

from django.apps import apps
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from common.optimization import optimize_image, optimize_video
from common.utils.files import get_sanitized_filename
from common.utils.images import convert_image_to_avif


class Command(BaseCommand):
    """
    EN:
    Management command to optimize all existing images and videos across the project.
    It iterates through specified models and fields to apply optimization.

    FA:
    دستور مدیریتی برای بهینه‌سازی تمامی تصاویر و ویدیوهای موجود در پروژه.
    این دستور از طریق مدل‌ها و فیلدهای مشخص شده، بهینه‌سازی را اعمال می‌کند.
    """

    help = "Optimizes all existing images and videos in the project."

    def handle(self, *args, **options):
        """
        EN: Main execution logic for the optimize_files command.
        FA: منطق اصلی اجرای دستور optimize_files.
        """
        self.stdout.write("Starting file optimization...")

        # EN: List of models and fields to optimize
        # FA: لیستی از مدل‌ها و فیلدها برای بهینه‌سازی
        models_to_optimize = {
            "users.User": ["profile_picture"],
            "medias.Media": ["storage_key"],
        }

        for model_str, field_names in models_to_optimize.items():
            try:
                model = apps.get_model(model_str)
                self.stdout.write(f"Optimizing {model_str}...")

                for obj in model.objects.all():
                    for field_name in field_names:
                        field_value = getattr(obj, field_name)
                        if not field_value:
                            continue

                        # EN: Case 1: Standard ImageField/FileField (e.g., User.profile_picture)
                        # FA: مورد اول: ImageField یا FileField استاندارد
                        if hasattr(field_value, "path") and hasattr(
                            field_value, "save"
                        ):
                            try:
                                # EN: Skip if already AVIF
                                # FA: اگر قبلاً AVIF شده باشد، رد شود
                                if field_value.name.lower().endswith(".avif"):
                                    continue

                                content_type = ""
                                if hasattr(field_value, "file") and hasattr(
                                    field_value.file, "content_type"
                                ):
                                    content_type = field_value.file.content_type

                                if (
                                    "image" in content_type
                                    or field_value.name.lower().endswith(
                                        (".jpg", ".jpeg", ".png", ".webp")
                                    )
                                ):
                                    self.stdout.write(
                                        f"  Optimizing image field {field_name} for {model_str} ID {obj.pk}..."
                                    )
                                    result = optimize_image(field_value)
                                    if result:
                                        # EN: Use field.save to handle storage and database update
                                        # FA: استفاده از field.save برای مدیریت ذخیره‌سازی و به‌روزرسانی پایگاه داده
                                        field_value.save(
                                            result["filename"],
                                            result["buffer"],
                                            save=True,
                                        )
                                elif (
                                    "video" in content_type
                                    or field_value.name.lower().endswith(
                                        (".mp4", ".mov", ".avi", ".mkv")
                                    )
                                ):
                                    if "_optimized" not in field_value.name:
                                        self.stdout.write(
                                            f"  Queuing video optimization for {field_name} in {model_str} ID {obj.pk}..."
                                        )
                                        optimize_video.delay(field_value.path)
                            except Exception as e:
                                self.stderr.write(
                                    self.style.ERROR(
                                        f"Error optimizing field {field_name} for {model_str} ID {obj.pk}: {e}"
                                    )
                                )

                        # EN: Case 2: CharField storing storage path (e.g., Media.storage_key)
                        # FA: مورد دوم: CharField که مسیر ذخیره‌سازی را نگه می‌دارد
                        elif (
                            isinstance(field_value, str)
                            and model_str == "medias.Media"
                            and field_name == "storage_key"
                        ):
                            if obj.type == "image" and not field_value.lower().endswith(
                                ".avif"
                            ):
                                try:
                                    self.stdout.write(
                                        f"  Optimizing Media storage_key for ID {obj.pk}..."
                                    )
                                    original_storage_key = field_value
                                    if default_storage.exists(original_storage_key):
                                        with default_storage.open(
                                            original_storage_key, "rb"
                                        ) as f:
                                            optimized_image_content = (
                                                convert_image_to_avif(f)
                                            )

                                        sanitized_name = get_sanitized_filename(
                                            optimized_image_content.name
                                        )
                                        base_name, _ = os.path.splitext(sanitized_name)
                                        new_storage_key = f"{base_name}.avif"

                                        saved_path = default_storage.save(
                                            new_storage_key, optimized_image_content
                                        )

                                        # EN: Update media object attributes manually
                                        # FA: به‌روزرسانی دستی ویژگی‌های شیء رسانه
                                        obj.storage_key = saved_path
                                        obj.url = default_storage.url(saved_path)
                                        obj.mime = "image/avif"
                                        obj.save()

                                        # EN: Remove old file from storage
                                        # FA: حذف فایل قدیمی از فضای ذخیره‌سازی
                                        if default_storage.exists(original_storage_key):
                                            default_storage.delete(original_storage_key)
                                except Exception as e:
                                    self.stderr.write(
                                        self.style.ERROR(
                                            f"Error optimizing Media ID {obj.pk}: {e}"
                                        )
                                    )

            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f"Error optimizing {model_str}: {e}")
                )

        self.stdout.write(self.style.SUCCESS("File optimization complete."))
