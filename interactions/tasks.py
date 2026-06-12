import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def notify_author_on_new_comment(comment_id):
    """
    EN:
    Celery task to send a notification to the post author about a new comment.
    Current implementation is a placeholder for future notification systems.

    FA:
    تسک Celery برای ارسال اعلان به نویسنده پست در مورد یک نظر جدید.
    پیاده‌سازی فعلی یک جایگزین برای سیستم‌های اعلان آینده است.
    """
    # EN: Notifications are disabled for now.
    # FA: اعلان‌ها فعلاً غیرفعال هستند.
    pass
