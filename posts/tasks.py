from celery import shared_task

from .services import increment_article_view_count, publish_scheduled_articles


@shared_task
def increment_article_view_count_task(article_id):
    """
    EN: Celery task to increment the view count of an article.
    FA: تسک Celery برای افزایش تعداد بازدیدهای یک مقاله.
    """
    increment_article_view_count(article_id)


@shared_task
def publish_scheduled_articles_task():
    """
    EN: Periodic Celery task to publish articles that are scheduled for the current time.
    FA: تسک دوره‌ای Celery برای انتشار مقاله‌هایی که برای زمان فعلی زمان‌بندی شده‌اند.
    """
    publish_scheduled_articles()
