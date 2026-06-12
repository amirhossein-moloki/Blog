from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from users.models import User


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """
    EN:
    Handles actions to be taken after a user is saved.
    Mainly used for invalidating user-related cache entries.

    FA:
    مدیریت عملیاتی که پس از ذخیره شدن یک کاربر باید انجام شود.
    عمدتاً برای ابطال ورودی‌های کش مرتبط با کاربر استفاده می‌شود.
    """
    # EN: Invalidate user-specific dashboard cache
    # FA: ابطال کش داشبورد مخصوص کاربر
    cache.delete(f"dashboard:user:{instance.id}")


@receiver(post_delete, sender=User)
def user_post_delete(sender, instance, **kwargs):
    """
    EN:
    Invalidates cache when a user is deleted.
    Ensures that stale data is not served from the cache.

    FA:
    ابطال کش هنگام حذف یک کاربر.
    اطمینان حاصل می‌کند که داده‌های قدیمی از کش ارائه نمی‌شوند.
    """
    cache.delete(f"dashboard:user:{instance.id}")
