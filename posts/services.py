import json
import logging
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import F
from django.utils import timezone

from medias.models import Media
from posts.blocks import block_registry

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


def validate_and_sanitize_blocks(blocks, language_code="en"):
    """
    Performs full validation, sanitization, and normalization on content blocks list.
    """
    if not isinstance(blocks, list):
        raise ValidationError("Content blocks must be a list of blocks.")

    # 1. Payload size check
    serialized_size = len(json.dumps(blocks).encode("utf-8"))
    if serialized_size > 5 * 1024 * 1024:
        raise ValidationError("Request payload size exceeds 5 Megabytes limit.")

    # 2. Maximum block count check
    if len(blocks) > 200:
        raise ValidationError("Maximum block count of 200 blocks exceeded.")

    # 3. Registry & Schema checks, ID duplicate check, and position duplicate check
    seen_ids = set()
    seen_orders = set()
    media_ids_to_check = set()

    for idx, block in enumerate(blocks):
        # Validate base structure using block registry
        block_registry.validate_block_payload(block)

        block_id = block.get("id")
        if block_id in seen_ids:
            raise ValidationError(
                {
                    f"content_blocks[{idx}].id": f"Duplicate block ID detected: '{block_id}'."
                }
            )
        seen_ids.add(block_id)

        order = block.get("order")
        if order in seen_orders:
            raise ValidationError(
                {
                    f"content_blocks[{idx}].order": f"Duplicate block order detected: '{order}'."
                }
            )
        seen_orders.add(order)

        # Collect media_id and media_ids to validate in bulk (fully generically)
        b_type = block.get("type")
        b_data = block.get("data", {})
        handler = block_registry.get_block(b_type)
        if handler:
            media_ids_to_check.update(handler.get_referenced_media_ids(b_data))

    # 4. Check that media IDs actually exist and are active
    if media_ids_to_check:
        existing_active_media_ids = set(
            Media.objects.filter(id__in=media_ids_to_check, is_active=True).values_list(
                "id", flat=True
            )
        )
        missing_ids = media_ids_to_check - existing_active_media_ids
        if missing_ids:
            for idx, block in enumerate(blocks):
                b_type = block.get("type")
                b_data = block.get("data", {})
                handler = block_registry.get_block(b_type)
                if handler:
                    block_m_ids = handler.get_referenced_media_ids(b_data)
                    overlapping = block_m_ids & missing_ids
                    if overlapping:
                        mid = list(overlapping)[0]
                        if language_code == "fa":
                            msg = f"رسانه‌ای با شناسه {mid} در کتابخانه رسانه‌ها وجود ندارد."
                        else:
                            msg = f"Media with ID {mid} does not exist in the media library."

                        # Target specific field based on the block type structure
                        if b_type == "gallery":
                            g_idx = b_data.get("media_ids", []).index(mid)
                            raise ValidationError(
                                {f"content_blocks[{idx}].data.media_ids[{g_idx}]": msg}
                            )
                        else:
                            raise ValidationError(
                                {f"content_blocks[{idx}].data.media_id": msg}
                            )

    # 5. Empty block detection (fully generically)
    for idx, block in enumerate(blocks):
        b_type = block.get("type")
        b_data = block.get("data", {})
        handler = block_registry.get_block(b_type)
        if handler and handler.is_empty(b_data):
            if b_type == "paragraph":
                raise ValidationError(
                    {
                        f"content_blocks[{idx}].data.text": "Empty paragraph blocks are not allowed."
                    }
                )
            elif b_type == "image":
                raise ValidationError(
                    {
                        f"content_blocks[{idx}].data.media_id": "Image block must have a media_id."
                    }
                )
            else:
                raise ValidationError(
                    {f"content_blocks[{idx}]": f"Block of type '{b_type}' is empty."}
                )

    # 6. Heading hierarchy validation
    headings = []
    for idx, block in enumerate(blocks):
        if block.get("type") == "heading":
            headings.append((idx, block.get("data", {}).get("level")))

    seen_levels = set()
    for b_idx, lvl in headings:
        if lvl > 1:
            if (lvl - 1) not in seen_levels and lvl > 2:
                raise ValidationError(
                    {
                        f"content_blocks[{b_idx}].data.level": f"Heading hierarchy violation: Heading level {lvl} must be preceded by level {lvl - 1}."
                    }
                )
        seen_levels.add(lvl)

    # 7. HTML Sanitization on all text inputs using BeautifulSoup
    def sanitize_dict(d):
        for k, v in d.items():
            if isinstance(v, str):
                soup = BeautifulSoup(v, "html.parser")
                for bad_tag in soup(["script", "style", "embed", "object"]):
                    bad_tag.decompose()
                for tag in soup.find_all(True):
                    bad_attrs = [
                        attr
                        for attr in tag.attrs
                        if attr.startswith("on")
                        or attr == "src"
                        and "javascript:" in tag[attr]
                    ]
                    for attr in bad_attrs:
                        del tag[attr]
                d[k] = str(soup)
            elif isinstance(v, dict):
                sanitize_dict(v)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        sanitize_dict(item)

    for block in blocks:
        sanitize_dict(block.get("data", {}))

    # 8. Sort blocks by order and normalize them so orders are contiguous integers starting from 1
    blocks.sort(key=lambda b: b.get("order", 0))
    for i, block in enumerate(blocks, start=1):
        block["order"] = i

    return blocks


def calculate_blocks_reading_time(blocks):
    """
    Auto-calculates reading time based on word count of text components inside all blocks.
    """
    if not blocks:
        return 0
    text_content = []

    def extract_text(d):
        for k, v in d.items():
            if isinstance(v, str):
                soup = BeautifulSoup(v, "html.parser")
                text_content.append(soup.get_text())
            elif isinstance(v, dict):
                extract_text(v)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        extract_text(item)
                    elif isinstance(item, str):
                        text_content.append(item)

    for block in blocks:
        extract_text(block.get("data", {}))

    combined_text = " ".join(text_content)
    words = re.findall(r"\w+", combined_text)
    word_count = len(words)
    reading_time_minutes = word_count / 200
    return int(reading_time_minutes * 60)


def sync_article_media(obj):
    """
    EN:
    Synchronizes the Media attachments for an article or its translation based on
    the cover image, OG image, and any media mentioned within the HTML content or JSON blocks.

    FA:
    همگام‌سازی پیوست‌های رسانه‌ای برای یک مقاله یا ترجمه آن بر اساس تصویر کاور،
    تصویر OG و هر رسانه‌ای که در محتوای HTML یا بلاک‌های JSON ذکر شده است.
    """
    from .models import Article, ArticleTranslation

    if isinstance(obj, Article):
        article = obj
    elif isinstance(obj, ArticleTranslation):
        article = obj.article
    else:
        logger.error(f"Unsupported object type for sync_article_media: {type(obj)}")
        return

    # EN: Handle cover image and OG image synchronization (tied to the Article)
    if isinstance(obj, Article):
        # Handle cover
        article.media_attachments.filter(attachment_type="cover").exclude(
            media=article.cover_image
        ).delete()
        if article.cover_image:
            article.media_attachments.get_or_create(
                media=article.cover_image, attachment_type="cover"
            )

        # Handle OG image
        article.media_attachments.filter(attachment_type="og-image").exclude(
            media=article.og_image
        ).delete()
        if article.og_image:
            article.media_attachments.get_or_create(
                media=article.og_image, attachment_type="og-image"
            )

    # EN: Handle in-content media (Only for ArticleTranslation, where content/blocks reside)
    if isinstance(obj, ArticleTranslation):
        content = obj.content
        content_blocks = obj.content_blocks or []
        linked_media_ids = set()

        # 1. Extract from content_blocks if present (fully generically)
        if content_blocks:
            for block in content_blocks:
                b_type = block.get("type")
                b_data = block.get("data", {})
                handler = block_registry.get_block(b_type)
                if handler:
                    linked_media_ids.update(handler.get_referenced_media_ids(b_data))

        # 2. Fallback to HTML-based content images if blocks are not used/empty
        if not linked_media_ids and content:
            media_paths_in_content = set()
            urls = re.findall(r'<img [^>]*src="([^"]+)"', content) + re.findall(
                r"<img [^>]*src='([^']+)'", content
            )
            for url in urls:
                path = urlparse(url).path
                if path.startswith(settings.MEDIA_URL):
                    media_paths_in_content.add(
                        path[len(settings.MEDIA_URL) :].lstrip("/")
                    )

            if media_paths_in_content:
                linked_media_ids = set(
                    Media.objects.filter(
                        storage_key__in=media_paths_in_content
                    ).values_list("id", flat=True)
                )

        current_media_ids = set(
            article.media_attachments.filter(attachment_type="in-content").values_list(
                "media_id", flat=True
            )
        )

        # Add new media attachments found
        ids_to_add = linked_media_ids - current_media_ids
        for media_id in ids_to_add:
            # Validate that Media exists before linking
            if Media.objects.filter(pk=media_id).exists():
                article.media_attachments.get_or_create(
                    media_id=media_id, attachment_type="in-content"
                )

        # Remove media attachments that are no longer referenced
        ids_to_remove = current_media_ids - linked_media_ids
        if ids_to_remove:
            article.media_attachments.filter(
                media_id__in=ids_to_remove, attachment_type="in-content"
            ).delete()
