"""
EN: Imports and exposes common cache tasks for Celery autodiscovery.
FA: ایمپورت و ارائه تسک‌های کش برای کشف خودکار توسط Celery.
"""

from .cache.tasks import (
    warmup_article_detail,
    warmup_category_pages,
    warmup_homepage,
    warmup_related_content,
)

__all__ = [
    "warmup_homepage",
    "warmup_article_detail",
    "warmup_category_pages",
    "warmup_related_content",
]
