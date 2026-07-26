"""
EN: Configuration class for the common application. Registers cache signals and warmup builders on startup.
FA: کلاس تنظیمات برای اپلیکیشن common. ثبت سیگنال‌های کش و سازنده‌های پیش‌گرم کردن کش در زمان راه‌اندازی.
"""

import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class CommonConfig(AppConfig):
    """
    EN: AppConfig class for common module. Registers signal handlers and warmup builders.
    FA: کلاس AppConfig برای ماژول common. ثبت سیگنال‌های ابطال کش و سازنده‌های پیش‌گرم کردن کش.
    """

    name = "common"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        """
        EN: Registers cache signals and warmup builders upon application startup.
        FA: ثبت سیگنال‌های کش و کالبک‌های پیش‌گرم کردن کش به هنگام بارگذاری کامل پروژه.
        """
        # EN: 1. Register Signals
        # FA: ۱. ثبت سیگنال‌ها
        from common.cache.signals import register_cache_signals

        register_cache_signals()

        # EN: 1.5. Validate S3 settings if required
        # FA: ۱.۵. اعتبارسنجی تنظیمات S3 در صورت لزوم
        import os

        from django.conf import settings
        from django.core.exceptions import ImproperlyConfigured

        backup_storage = getattr(settings, "BACKUP_STORAGE", "local")
        offsite_enabled = getattr(settings, "BACKUP_OFFSITE_ENABLED", False)
        offsite_required = getattr(settings, "BACKUP_OFFSITE_REQUIRED", False)

        bucket_name = os.environ.get("AWS_STORAGE_BUCKET_NAME") or getattr(
            settings, "AWS_STORAGE_BUCKET_NAME", None
        )

        s3_configured = bool(bucket_name)

        if offsite_required:
            if not s3_configured:
                raise ImproperlyConfigured(
                    "S3 Backup/Object Storage is required in Production but credentials or bucket name are missing. "
                    "Ensure AWS_STORAGE_BUCKET_NAME, AWS_ACCESS_KEY_ID, and AWS_SECRET_ACCESS_KEY are set."
                )
        elif offsite_enabled or "s3" in backup_storage:
            if not s3_configured:
                logger.warning(
                    "S3 backup disabled (Development Mode) - Missing S3 credentials or bucket name."
                )

        # EN: 2. Register Warmup Builders
        # FA: ۲. ثبت سازنده‌های پیش‌گرم کردن کش
        try:
            from common.cache import build_cache_key, warmup_service
            from posts.models import Article, Category
            from posts.serializers import ArticleListSerializer, CategorySerializer

            def build_homepage() -> dict:
                # EN: Fetch latest 10 published articles for homepage cache
                # FA: دریافت ۱۰ مقاله آخر منتشر شده برای کش صفحه اصلی
                articles = Article.objects.filter(status="published").order_by(
                    "-published_at", "-id"
                )[:10]
                serializer = ArticleListSerializer(articles, many=True)
                return {
                    "data": serializer.data,
                    "pagination": {
                        "pageNo": 1,
                        "pageSize": 10,
                        "totalPage": 1,
                        "totalCount": len(articles),
                        "lastId": None,
                    },
                    "messagesList": [],
                }

            def build_categories_list() -> list:
                # EN: Fetch all categories
                # FA: دریافت کلیه دسته‌بندی‌ها
                cats = Category.objects.select_related("parent").all()
                return CategorySerializer(cats, many=True).data

            # EN: Build keys and register
            # FA: ساخت کلیدها و ثبت آن‌ها در سرویس پیش‌گرم کردن
            homepage_key = build_cache_key(
                "posts",
                "article_list",
                "list",
                params={"page": "1", "pagesize": "10"},
                lang="en",
            )
            warmup_service.register_builder(
                name="homepage",
                key=homepage_key,
                callback=build_homepage,
                group="homepage",
                soft_ttl=300,
                hard_ttl=900,
            )

            categories_key = build_cache_key("posts", "category_list", "list")
            warmup_service.register_builder(
                name="categories_list",
                key=categories_key,
                callback=build_categories_list,
                group="categories",
                soft_ttl=86400,
                hard_ttl=604800,
            )

            logger.info("Enterprise Cache Warmup builders registered successfully.")
        except Exception as e:
            logger.warning(f"Could not register Warmup Builders during startup: {e}")
