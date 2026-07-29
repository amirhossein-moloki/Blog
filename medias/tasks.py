import logging

from celery import shared_task

from .models import Media

logger = logging.getLogger(__name__)


@shared_task
def generate_image_variants_task(media_id):
    """
    EN: Async background worker task to generate variants.
    FA: تسک ناهمگام ورکر پس‌زمینه برای تولید نسخه‌های مختلف تصویر.
    """
    try:
        media_instance = Media.objects.get(pk=media_id)
        media_instance.status = "Processing"
        media_instance.save(update_fields=["status"])

        from .services import ImageProcessor

        ImageProcessor.generate_variants(media_instance)

        media_instance.status = "Ready"
        media_instance.save(update_fields=["status"])
        logger.info(f"Successfully generated variants for Media ID: {media_id}")
    except Exception as e:
        logger.error(
            f"Error in generate_image_variants_task for Media ID {media_id}: {e}"
        )
        try:
            media_instance = Media.objects.get(pk=media_id)
            media_instance.status = "Rejected"
            media_instance.save(update_fields=["status"])
        except Exception:
            pass
