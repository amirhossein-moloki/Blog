from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from users.models import User

@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """
    Handles actions to be taken after a user is saved.
    - Invalidate user-related cache.
    """
    # Invalidate user-specific dashboard cache
    cache.delete(f"dashboard:user:{instance.id}")

@receiver(post_delete, sender=User)
def user_post_delete(sender, instance, **kwargs):
    """
    Invalidates cache when a user is deleted.
    """
    cache.delete(f"dashboard:user:{instance.id}")
