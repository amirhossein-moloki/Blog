from django.core.management.base import BaseCommand
from django.db.models import Q

from common.tasks import convert_image_to_avif_task
from medias.models import Media


class Command(BaseCommand):
    """
    EN:
    Management command to find existing non-AVIF images and queue them for conversion.
    This helps in optimizing old images that were uploaded before the AVIF conversion was implemented.

    FA:
    دستور مدیریتی برای یافتن تصاویر غیر AVIF موجود و صف‌بندی آن‌ها برای تبدیل.
    این کار به بهینه‌سازی تصاویر قدیمی که قبل از پیاده‌سازی تبدیل AVIF آپلود شده بودند کمک می‌کند.
    """

    help = "Finds all non-AVIF images and queues them for conversion to AVIF."

    def handle(self, *args, **options):
        """
        EN: Main logic to identify and queue images for processing.
        FA: منطق اصلی برای شناسایی و صف‌بندی تصاویر جهت پردازش.
        """
        self.stdout.write(self.style.NOTICE("Searching for images to process..."))

        images_to_process = Media.objects.filter(
            Q(type="image") & ~Q(mime="image/avif")
        )

        count = images_to_process.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("No images to process."))
            return

        self.stdout.write(self.style.NOTICE(f"Found {count} image(s) to process."))

        for media in images_to_process:
            # EN: Trigger the conversion task for each identified image.
            # FA: اجرای تسک تبدیل برای هر تصویر شناسایی شده.
            convert_image_to_avif_task.delay(
                app_label="medias",
                model_name="media",
                instance_pk=media.id,
                field_name="storage_key",  # Note: storage_key is used as the file field in Media
            )
            self.stdout.write(f"Queued task for Media ID: {media.id}")

        self.stdout.write(self.style.SUCCESS(f"Successfully queued {count} task(s)."))
