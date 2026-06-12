from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    """
    EN: Application configuration for the 'users' app.
    FA: تنظیمات اپلیکیشن برای بخش کاربران ('users').
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "users"
    verbose_name = _("Users")

    def ready(self):
        """
        EN: Registers signals when the app is ready.
        FA: ثبت سیگنال‌ها هنگام آماده شدن اپلیکیشن.
        """
        import users.signals  # noqa: F401
