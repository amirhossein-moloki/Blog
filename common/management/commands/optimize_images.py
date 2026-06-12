import os

from django.core.management.base import BaseCommand
from django.db.models import Q

from common.utils.files import get_sanitized_filename
from common.utils.images import convert_image_to_avif
from medias.models import Media
from users.models import User


class Command(BaseCommand):
    """
    EN:
    Management command to optimize existing images in the database by converting them to AVIF format.
    It processes both user profile pictures and media library files.

    FA:
    دستور مدیریتی برای بهینه‌سازی تصاویر موجود در پایگاه داده با تبدیل آن‌ها به فرمت AVIF.
    این دستور هم تصاویر پروفایل کاربران و هم فایل‌های کتابخانه رسانه را پردازش می‌کند.
    """

    help = "Optimizes existing images in the database to AVIF format."

    def add_arguments(self, parser):
        """
        EN: Defines command line arguments for quality and speed.
        FA: تعریف آرگومان‌های خط فرمان برای کیفیت و سرعت.
        """
        parser.add_argument(
            "--quality", type=int, default=50, help="AVIF quality (0-100)"
        )
        parser.add_argument(
            "--speed", type=int, default=6, help="AVIF conversion speed (0-10)"
        )

    def handle(self, *args, **options):
        """
        EN: Main execution logic for the optimize_images command.
        FA: منطق اصلی اجرای دستور optimize_images.
        """
        quality = options["quality"]
        speed = options["speed"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting image optimization with quality={quality} and speed={speed}..."
            )
        )

        self.optimize_user_profiles(quality, speed)
        self.optimize_media_files(quality, speed)

        self.stdout.write(
            self.style.SUCCESS("Image optimization finished successfully!")
        )

    def optimize_user_profiles(self, quality, speed):
        """
        EN: Iterates through users and optimizes their profile pictures.
        FA: پیمایش کاربران و بهینه‌سازی تصاویر پروفایل آن‌ها.
        """
        self.stdout.write("Optimizing user profile pictures...")
        from django.core.files.storage import default_storage

        users = User.objects.exclude(profile_picture__isnull=True).exclude(
            profile_picture__exact=""
        )
        optimized_count = 0
        skipped_count = 0
        error_count = 0
        for user in users:
            try:
                if user.profile_picture.name.endswith(".avif"):
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipping already optimized profile picture for user {user.username}"
                        )
                    )
                    skipped_count += 1
                    continue

                self.stdout.write(
                    f"Optimizing profile picture for user {user.username}..."
                )

                original_name = user.profile_picture.name
                with default_storage.open(original_name, "rb") as f:
                    optimized_image_content = convert_image_to_avif(
                        f, quality=quality, speed=speed
                    )

                # EN: Save the new file
                # FA: ذخیره فایل جدید
                user.profile_picture.save(
                    optimized_image_content.name, optimized_image_content, save=True
                )

                # EN: Delete the old file
                # FA: حذف فایل قدیمی
                if default_storage.exists(original_name):
                    default_storage.delete(original_name)

                optimized_count += 1

            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(
                        f"Error optimizing profile picture for user {user.username}: {e}"
                    )
                )
                error_count += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Finished optimizing user profile pictures. Optimized: {optimized_count}, Skipped: {skipped_count}, Errors: {error_count}"
            )
        )

    def optimize_media_files(self, quality, speed):
        """
        EN: Iterates through media objects and optimizes image files.
        FA: پیمایش اشیاء رسانه و بهینه‌سازی فایل‌های تصویر.
        """
        self.stdout.write("Optimizing media files...")
        from django.core.files.storage import default_storage

        media_files = Media.objects.filter(Q(mime__startswith="image/")).exclude(
            storage_key__endswith=".avif"
        )

        optimized_count = 0
        skipped_count = 0
        error_count = 0

        for media in media_files:
            try:
                self.stdout.write(f"Optimizing media file {media.storage_key}...")

                original_storage_key = media.storage_key

                if not default_storage.exists(original_storage_key):
                    self.stderr.write(
                        self.style.ERROR(
                            f"File not found for media {media.storage_key}"
                        )
                    )
                    error_count += 1
                    continue

                with default_storage.open(original_storage_key, "rb") as f:
                    optimized_image_content = convert_image_to_avif(
                        f, quality=quality, speed=speed
                    )

                # EN: Get a sanitized name for the new file
                # FA: دریافت یک نام پاکسازی شده برای فایل جدید
                sanitized_name = get_sanitized_filename(optimized_image_content.name)

                # EN: Ensure the final name has a .avif extension
                # FA: اطمینان از اینکه نام نهایی دارای پسوند .avif باشد
                base_name, _ = os.path.splitext(sanitized_name)
                new_storage_key = f"{base_name}.avif"

                # EN: Save the new file
                # FA: ذخیره فایل جدید
                saved_path = default_storage.save(
                    new_storage_key, optimized_image_content
                )

                # EN: Update media object
                # FA: به‌روزرسانی شیء رسانه
                media.storage_key = saved_path
                media.url = default_storage.url(saved_path)
                media.mime = "image/avif"
                media.save()

                # EN: Remove old file
                # FA: حذف فایل قدیمی
                if default_storage.exists(original_storage_key):
                    default_storage.delete(original_storage_key)

                optimized_count += 1

            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(
                        f"Error optimizing media file {media.storage_key}: {e}"
                    )
                )
                error_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Finished optimizing media files. Optimized: {optimized_count}, Skipped: {skipped_count}, Errors: {error_count}"
            )
        )
