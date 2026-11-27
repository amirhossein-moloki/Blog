from django.apps import AppConfig


class MediasConfig(AppConfig):
    """
    EN: Application configuration for the 'medias' app.
    FA: تنظیمات اپلیکیشن برای بخش رسانه‌ها ('medias').
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "medias"

    def ready(self):
        try:
            import pillow_avif  # noqa: F401
        except ImportError:
            pass
        import medias.signals  # noqa: F401
