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

        # EN: 2. Register Warmup Builders
        # FA: ۲. ثبت سازنده‌های پیش‌گرم کردن کش
        try:
            from common.cache import warmup_service, build_cache_key
            from posts.models import Article, Category
            from posts.serializers import ArticleListSerializer, CategorySerializer

            def build_homepage() -> dict:
                # EN: Fetch latest 10 published articles for homepage cache
                # FA: دریافت ۱۰ مقاله آخر منتشر شده برای کش صفحه اصلی
                articles = Article.objects.filter(status="published").order_by("-published_at", "-id")[:10]
                serializer = ArticleListSerializer(articles, many=True)
                return {
                    "data": serializer.data,
                    "pagination": {
                        "pageNo": 1,
                        "pageSize": 10,
                        "totalPage": 1,
                        "totalCount": len(articles),
                        "lastId": None
                    },
                    "messagesList": []
                }

            def build_categories_list() -> list:
                # EN: Fetch all categories
                # FA: دریافت کلیه دسته‌بندی‌ها
                cats = Category.objects.select_related("parent").all()
                return CategorySerializer(cats, many=True).data

            # EN: Build keys and register
            # FA: ساخت کلیدها و ثبت آن‌ها در سرویس پیش‌گرم کردن
            homepage_key = build_cache_key("posts", "article_list", "list", params={"page": "1", "pagesize": "10"}, lang="en")
            warmup_service.register_builder(
                name="homepage",
                key=homepage_key,
                callback=build_homepage,
                group="homepage",
                soft_ttl=300,
                hard_ttl=900
            )

            categories_key = build_cache_key("posts", "category_list", "list")
            warmup_service.register_builder(
                name="categories_list",
                key=categories_key,
                callback=build_categories_list,
                group="categories",
                soft_ttl=86400,
                hard_ttl=604800
            )

            logger.info("Enterprise Cache Warmup builders registered successfully.")
        except Exception as e:
            logger.warning(f"Could not register Warmup Builders during startup: {e}")
