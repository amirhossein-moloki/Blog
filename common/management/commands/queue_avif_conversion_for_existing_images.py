# common/management/commands/queue_avif_conversion_for_existing_images.py

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db.models import ImageField

from common.tasks import convert_image_to_avif_task


class Command(BaseCommand):
    help = "Queues all existing images in the system for conversion to AVIF format."

    def handle(self, *args, **options):
        self.stdout.write("Starting to scan models for image fields...")

        # List of models to be scanned
        # You can edit this list to restrict the scan
        models_to_scan = apps.get_models()

        total_tasks_queued = 0

        for model in models_to_scan:
            image_fields = [
                f for f in model._meta.get_fields() if isinstance(f, ImageField)
            ]

            if not image_fields:
                continue

            self.stdout.write(f"  Scanning model: {model.__name__}")

            for instance in model.objects.all():
                for field in image_fields:
                    field_name = field.name
                    try:
                        image_field = getattr(instance, field_name)

                        # If the image field has a value and is not yet AVIF
                        if (
                            image_field
                            and hasattr(image_field, "name")
                            and image_field.name
                            and not image_field.name.lower().endswith(".avif")
                        ):
                            self.stdout.write(
                                f"    -> Queuing task for {model.__name__} ID: {instance.pk}, field: {field_name}"
                            )
                            convert_image_to_avif_task.delay(
                                app_label=model._meta.app_label,
                                model_name=model._meta.model_name,
                                instance_pk=instance.pk,
                                field_name=field_name,
                            )
                            total_tasks_queued += 1

                    except Exception as e:
                        self.stderr.write(
                            self.style.ERROR(
                                f"Error processing {model.__name__} ID: {instance.pk}, field: {field_name}: {e}"
                            )
                        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Operation completed successfully. Total tasks queued: {total_tasks_queued}"
            )
        )
