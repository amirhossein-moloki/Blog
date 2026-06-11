import logging
import re
from urllib.parse import urlparse

from django.conf import settings
from django.db.models import F
from django.utils import timezone

from medias.models import Media

from .models import AuthorProfile, Post

logger = logging.getLogger(__name__)


def increment_post_view_count(post_id):
    try:
        Post.objects.filter(pk=post_id).update(views_count=F("views_count") + 1)
        logger.info(f"Incremented view count for Post ID: {post_id}")
    except Exception as e:
        logger.error(f"Error incrementing view count for Post ID {post_id}: {e}")


def publish_scheduled_posts():
    now = timezone.now()
    posts_to_publish = Post.objects.filter(status="scheduled", scheduled_at__lte=now)

    if posts_to_publish.exists():
        num_published = posts_to_publish.update(
            status="published", published_at=F("scheduled_at"), scheduled_at=None
        )
        logger.info(f"Successfully published {num_published} scheduled posts.")
    else:
        logger.info("No scheduled posts to publish.")


def sync_post_media(post):
    post.media_attachments.filter(attachment_type="cover").exclude(
        media=post.cover_media
    ).delete()
    if post.cover_media:
        post.media_attachments.update_or_create(
            media=post.cover_media, defaults={"attachment_type": "cover"}
        )

    post.media_attachments.filter(attachment_type="og-image").exclude(
        media=post.og_image
    ).delete()
    if post.og_image:
        post.media_attachments.update_or_create(
            media=post.og_image, defaults={"attachment_type": "og-image"}
        )

    media_paths_in_content = set()
    for url in re.findall(r'<img [^>]*src="([^"]+)"', post.content):
        path = urlparse(url).path
        if path.startswith(settings.MEDIA_URL):
            media_paths_in_content.add(path[len(settings.MEDIA_URL) :].lstrip("/"))

    linked_media_ids = set(
        Media.objects.filter(storage_key__in=media_paths_in_content).values_list(
            "id", flat=True
        )
    )

    current_media_ids = set(
        post.media_attachments.filter(attachment_type="in-content").values_list(
            "media_id", flat=True
        )
    )

    ids_to_add = linked_media_ids - current_media_ids
    for media_id in ids_to_add:
        post.media_attachments.create(media_id=media_id, attachment_type="in-content")

    ids_to_remove = current_media_ids - linked_media_ids
    post.media_attachments.filter(
        media_id__in=ids_to_remove, attachment_type="in-content"
    ).delete()
