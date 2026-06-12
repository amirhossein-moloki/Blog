from django.apps import AppConfig


class PostsConfig(AppConfig):
    """
    EN: Application configuration for the 'posts' app.
    FA: تنظیمات اپلیکیشن برای بخش پست‌ها ('posts').
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "posts"

    def ready(self):
        """
        EN: Registers signals when the app is ready.
        FA: ثبت سیگنال‌ها هنگام آماده شدن اپلیکیشن.
        """
        import posts.signals  # noqa: F401
