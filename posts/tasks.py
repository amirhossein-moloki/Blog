from celery import shared_task

from .services import increment_post_view_count, publish_scheduled_posts


@shared_task
def increment_post_view_count_task(post_id):
    """
    EN: Celery task to increment the view count of a post.
    FA: تسک Celery برای افزایش تعداد بازدیدهای یک پست.
    """
    increment_post_view_count(post_id)


@shared_task
def publish_scheduled_posts_task():
    """
    EN: Periodic Celery task to publish posts that are scheduled for the current time.
    FA: تسک دوره‌ای Celery برای انتشار پست‌هایی که برای زمان فعلی زمان‌بندی شده‌اند.
    """
    publish_scheduled_posts()
