import logging
import re
from urllib.parse import urlparse

from django.conf import settings
from django.db.models import F
from django.utils import timezone

from medias.models import Media

from .models import Article

logger = logging.getLogger(__name__)


def increment_article_view_count(article_id):
    """
    EN: Asynchronously increments the view count for a specific article.
    FA: به طور نامتقارن تعداد بازدیدهای یک مقاله خاص را افزایش می‌دهد.
    """
    try:
        # EN: Use F() expression to prevent race conditions during concurrent updates.
        # FA: استفاده از عبارت F() برای جلوگیری از تداخل در به‌روزرسانی‌های همزمان.
        Article.objects.filter(pk=article_id).update(views_count=F("views_count") + 1)
        logger.info(f"Incremented view count for Article ID: {article_id}")
    except Exception as e:
        logger.error(f"Error incrementing view count for Article ID {article_id}: {e}")


def publish_scheduled_articles():
    """
    EN: Identifies and publishes all articles whose scheduled time has passed.
    FA: تمامی مقاله‌هایی که زمان زمان‌بندی آن‌ها فرا رسیده است را شناسایی و منتشر می‌کند.
    """
    now = timezone.now()
    articles_to_publish = Article.objects.filter(
        status="scheduled", scheduled_at__lte=now
    )

    if articles_to_publish.exists():
        num_published = articles_to_publish.update(
            status="published", published_at=F("scheduled_at"), scheduled_at=None
        )
        logger.info(f"Successfully published {num_published} scheduled articles.")
    else:
        logger.info("No scheduled articles to publish.")


def sync_article_media(obj):
    """
    EN:
    Synchronizes the Media attachments for an article or its translation based on
    the cover image, OG image, and any media mentioned within the HTML content.

    FA:
    همگام‌سازی پیوست‌های رسانه‌ای برای یک مقاله یا ترجمه آن بر اساس تصویر کاور،
    تصویر OG و هر رسانه‌ای که در محتوای HTML ذکر شده است.
    """
    from .models import Article, ArticleTranslation

    if isinstance(obj, Article):
        article = obj
        content = ""  # No content-based sync for the base article
    elif isinstance(obj, ArticleTranslation):
        article = obj.article
        content = obj.content
    else:
        logger.error(f"Unsupported object type for sync_article_media: {type(obj)}")
        return

    # EN: Handle cover image and OG image synchronization (tied to the Article)
    # FA: مدیریت همگام‌سازی تصویر کاور و تصویر OG (متصل به مقاله)
    if isinstance(obj, Article):
        # Handle cover
        article.media_attachments.filter(attachment_type="cover").exclude(
            media=article.cover_image
        ).delete()
        if article.cover_image:
            article.media_attachments.update_or_create(
                media=article.cover_image, defaults={"attachment_type": "cover"}
            )

        # Handle OG image
        article.media_attachments.filter(attachment_type="og-image").exclude(
            media=article.og_image
        ).delete()
        if article.og_image:
            article.media_attachments.update_or_create(
                media=article.og_image, defaults={"attachment_type": "og-image"}
            )

    # EN: Handle in-content media (tied to the content, which exists in ArticleTranslation)
    # FA: مدیریت رسانه‌های درون محتوا (متصل به محتوا، که در ArticleTranslation وجود دارد)
    if content:
        # EN: Parse content to find media mentioned in <img> tags (supports both double and single quotes)
        # FA: تجزیه محتوا برای یافتن رسانه‌های ذکر شده در تگ‌های <img> (پشتیبانی از هر دو نوع کوتیشن)
        media_paths_in_content = set()
        urls = re.findall(r'<img [^>]*src="([^"]+)"', content) + re.findall(
            r"<img [^>]*src='([^']+)'", content
        )
        for url in urls:
            path = urlparse(url).path
            if path.startswith(settings.MEDIA_URL):
                media_paths_in_content.add(path[len(settings.MEDIA_URL) :].lstrip("/"))

        linked_media_ids = set(
            Media.objects.filter(storage_key__in=media_paths_in_content).values_list(
                "id", flat=True
            )
        )

        current_media_ids = set(
            article.media_attachments.filter(attachment_type="in-content").values_list(
                "media_id", flat=True
            )
        )

        # EN: Add new media attachments found in content
        # FA: اضافه کردن پیوست‌های رسانه‌ای جدید یافت شده در محتوا
        ids_to_add = linked_media_ids - current_media_ids
        for media_id in ids_to_add:
            article.media_attachments.get_or_create(
                media_id=media_id, attachment_type="in-content"
            )

        # EN: Remove media attachments that are no longer in content
        # FA: حذف پیوست‌های رسانه‌ای که دیگر در محتوا نیستند
        # Note: In a multi-language setup, a media might be used in one translation but not another.
        # For simplicity, we keep it if it is used in ANY translation or we just manage it per sync.
        # Here we follow the original logic: remove what's not in the CURRENTly syncing content.
        ids_to_remove = current_media_ids - linked_media_ids
        if ids_to_remove:
            article.media_attachments.filter(
                media_id__in=ids_to_remove, attachment_type="in-content"
            ).delete()
