from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from .models import Media
from .services import MediaUsageService


@receiver(pre_delete, sender=Media)
def protect_media_deletion(sender, instance, **kwargs):
    """
    EN: Pre-delete signal to prevent deletion of Media that is still actively referenced.
    FA: سیگنال پیش از حذف برای جلوگیری از حذف رسانه‌ای که هنوز به آن ارجاع داده می‌شود.
    """
    # If the instance has a temporary bypass attribute (e.g., _allow_delete = True) we allow it.
    if getattr(instance, "_allow_delete", False):
        return

    usage = MediaUsageService.get_usage(instance)
    if usage["usage_count"] > 0:
        raise ValidationError(
            f"Cannot delete media {instance.id} because it is currently used by published content."
        )
