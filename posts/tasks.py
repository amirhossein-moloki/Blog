from celery import shared_task
from .services import increment_post_view_count, publish_scheduled_posts

@shared_task
def increment_post_view_count_task(post_id):
    increment_post_view_count(post_id)

@shared_task
def publish_scheduled_posts_task():
    publish_scheduled_posts()
