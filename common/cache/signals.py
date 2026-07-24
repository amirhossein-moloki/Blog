"""
EN: Event-driven cache invalidation and selective warmup listeners using Django signals.
FA: شنونده‌های ابطال کش رویدادمحور و پیش‌گرم کردن انتخابی کش با استفاده از سیگنال‌های جنگو.
"""

import logging

from django.db.models.signals import post_delete, post_save

# EN: Dynamic imports to prevent circular references
# FA: ایمپورت‌های پویا برای جلوگیری از رفرنس‌های حلقوی
from .manager import cache_manager
from .services import warmup_service

logger = logging.getLogger(__name__)


def invalidate_article_cache(sender, instance, **kwargs) -> None:
    """
    EN: Invalidates related article caches on save or delete of an Article.
    FA: ابطال کش‌های مرتبط با مقاله در زمان ذخیره یا حذف مقاله.
    """
    try:
        slug = (
            instance.translations.first().slug
            if hasattr(instance, "translations") and instance.translations.exists()
            else str(instance.id)
        )
    except Exception:
        slug = str(instance.id)

    logger.info(f"Signal received: Invalidate cache for Article: {slug}")

    # EN: 1. Version based invalidation for list of articles
    # FA: ۱. ابطال بر اساس نسخه برای لیست مقالات
    cache_manager.remove_by_version("articles")
    cache_manager.remove_by_version("latest_articles")
    cache_manager.remove_by_version("homepage")

    # EN: 2. Tag based invalidation for specific tags and categories
    # FA: ۲. ابطال بر اساس تگ برای دسته‌بندی‌ها و تگ‌های خاص
    cache_manager.invalidation.invalidate_tag(f"article_detail:{slug}")
    if instance.category:
        cache_manager.invalidation.invalidate_tag(f"category:{instance.category.id}")

    # EN: 3. Trigger selective predictive Warmup
    # FA: ۳. آغاز پیش‌گرم کردن پیش‌بینانه انتخابی
    warmup_service.warmup_after_mutation(
        article_slug=slug,
        category_slug=instance.category.slug if instance.category else None,
    )


def invalidate_category_cache(sender, instance, **kwargs) -> None:
    """
    EN: Invalidates category-related caches on Category mutation.
    FA: ابطال کش‌های مرتبط با دسته‌بندی در زمان تغییر دسته‌بندی.
    """
    logger.info(f"Signal received: Invalidate Category: {instance.slug}")
    cache_manager.remove_by_version("categories")
    cache_manager.remove_by_version("homepage")
    cache_manager.invalidation.invalidate_tag(f"category:{instance.id}")
    cache_manager.invalidation.invalidate_tag(f"category_detail:{instance.slug}")

    warmup_service.warmup_after_mutation(category_slug=instance.slug)


def invalidate_tag_cache(sender, instance, **kwargs) -> None:
    """
    EN: Invalidates tag-related caches on Tag mutation.
    FA: ابطال کش‌های مرتبط با برچسب در زمان تغییر برچسب.
    """
    logger.info(f"Signal received: Invalidate Tag: {instance.slug}")
    cache_manager.remove_by_version("tags")
    cache_manager.invalidation.invalidate_tag(f"tag:{instance.id}")


def invalidate_comment_cache(sender, instance, **kwargs) -> None:
    """
    EN: Invalidates comments cache for an article when a comment is added/removed.
    FA: ابطال کش نظرات یک مقاله در زمان افزودن/حذف نظر.
    """
    if instance.article:
        try:
            slug = (
                instance.article.translations.first().slug
                if hasattr(instance.article, "translations")
                and instance.article.translations.exists()
                else str(instance.article.id)
            )
        except Exception:
            slug = str(instance.article.id)

        logger.info(f"Signal received: Invalidate comments for Article: {slug}")
        cache_manager.invalidation.invalidate_tag(f"comments:{slug}")


# EN: Setup signal connections safely
# FA: راه‌اندازی امن اتصالات سیگنال‌ها
def register_cache_signals() -> None:
    """
    EN: Connects Django signals to cache invalidation handlers.
    FA: اتصال سیگنال‌های جنگو به مدیریت‌کننده‌های ابطال کش.
    """
    try:
        from interactions.models import Comment
        from posts.models import Article, Category, Tag

        # EN: Article Signals
        # FA: سیگنال‌های مقاله
        post_save.connect(
            invalidate_article_cache, sender=Article, dispatch_uid="cache_article_save"
        )
        post_delete.connect(
            invalidate_article_cache,
            sender=Article,
            dispatch_uid="cache_article_delete",
        )

        # EN: Category Signals
        # FA: سیگنال‌های دسته‌بندی
        post_save.connect(
            invalidate_category_cache,
            sender=Category,
            dispatch_uid="cache_category_save",
        )
        post_delete.connect(
            invalidate_category_cache,
            sender=Category,
            dispatch_uid="cache_category_delete",
        )

        # EN: Tag Signals
        # FA: سیگنال‌های برچسب
        post_save.connect(
            invalidate_tag_cache, sender=Tag, dispatch_uid="cache_tag_save"
        )
        post_delete.connect(
            invalidate_tag_cache, sender=Tag, dispatch_uid="cache_tag_delete"
        )

        # EN: Comment Signals
        # FA: سیگنال‌های نظر
        post_save.connect(
            invalidate_comment_cache, sender=Comment, dispatch_uid="cache_comment_save"
        )
        post_delete.connect(
            invalidate_comment_cache,
            sender=Comment,
            dispatch_uid="cache_comment_delete",
        )

        logger.info("Enterprise Cache Signals registered successfully.")
    except Exception as e:
        logger.error(f"Failed to register Cache Signals: {e}", exc_info=True)
