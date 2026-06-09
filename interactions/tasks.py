from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task
def notify_author_on_new_comment(comment_id):
    """
    Celery task to send a notification to the post author about a new comment.
    """
    # Notifications are disabled for now.
    pass
