from django.apps import apps
from django.core.management.base import BaseCommand

from common.optimization import optimize_image, optimize_video


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
            "medias.Media": ["file"],
        }

        for model_str, field_names in models_to_optimize.items():
            try:
                model = apps.get_model(model_str)
                self.stdout.write(f"Optimizing {model_str}...")

                for obj in model.objects.all():
                    for field_name in field_names:
                        field = getattr(obj, field_name)
                        if field:
                            if hasattr(field, "path"):  # EN: For ImageField and FileField
                                                        # FA: برای ImageField و FileField
                                if "image" in field.file.content_type:
                                    optimize_image(field)
                                    obj.save()
                                elif "video" in field.file.content_type:
                                    optimize_video.delay(field.path)
                            elif isinstance(field, str) and field.startswith(
                                "/media/"
                            ):  # EN: For medias.Media
                                                # FA: برای medias.Media
                                # EN: This part is tricky as we don't have the file object directly
                                # FA: این بخش دشوار است زیرا مستقیماً به شیء فایل دسترسی نداریم
                                # EN: We'll need to find the file in the storage and optimize it
                                # FA: باید فایل را در فضای ذخیره‌سازی پیدا کرده و آن را بهینه‌سازی کنیم
                                pass

            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f"Error optimizing {model_str}: {e}")
                )

        self.stdout.write(self.style.SUCCESS("File optimization complete."))
