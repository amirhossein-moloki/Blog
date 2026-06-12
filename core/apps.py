from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CoreConfig(AppConfig):
    """
    EN:
    Core application configuration for shared project components.

    FA:
    تنظیمات اپلیکیشن Core برای اجزای مشترک پروژه.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = _("Core")
