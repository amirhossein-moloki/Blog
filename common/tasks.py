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
    A Celery task for asynchronously converting an image field to AVIF format.
    """
    try:
        # Find the model and object from the database
        Model = apps.get_model(app_label, model_name)
        instance = Model.objects.get(pk=instance_pk)

        image_field = getattr(instance, field_name)

        # If no file exists or it's already AVIF, do nothing
        if (
            not image_field
            or not image_field.name
            or image_field.name.lower().endswith(".avif")
        ):
            return f"No action needed for {model_name} {instance_pk}."

        original_name = image_field.name

        # 1. Convert the image to AVIF in memory. The utility returns a ContentFile.
        avif_content_file = convert_image_to_avif(
            image_field, quality=quality, speed=speed
        )

        # 2. Sanitize the filename and save the new file to storage.
        sanitized_name = get_sanitized_filename(avif_content_file.name)
        saved_name = default_storage.save(sanitized_name, avif_content_file)

        # 4. Update the model
        setattr(instance, field_name, saved_name)
        instance.save(update_fields=[field_name])

        # 5. Delete the original file (if different)
        if saved_name != original_name and default_storage.exists(original_name):
            default_storage.delete(original_name)

        return f"Successfully converted image for {model_name} {instance_pk}."

    except Model.DoesNotExist:
        # If the object was deleted before the task executed, it's fine
        return f"{model_name} with pk {instance_pk} not found. Skipping."
    except Exception as exc:
        # If an error occurs, Celery retries the task (up to 3 times)
        raise self.retry(exc=exc, countdown=60)  # Retry after 60 seconds
