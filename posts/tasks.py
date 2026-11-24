import logging

import requests
from celery import shared_task
from django.conf import settings

from .services import (
    flush_buffered_article_view_counts,
    increment_article_view_count,
    publish_scheduled_articles,
)

logger = logging.getLogger(__name__)


@shared_task
def increment_article_view_count_task(article_id):
    """
    EN: Celery task to increment the view count of an article.
    FA: تسک Celery برای افزایش تعداد بازدیدهای یک مقاله.
    """
    increment_article_view_count(article_id)


@shared_task
def flush_article_view_counts_task():
    """
    EN: Periodic Celery beat task to flush Redis-buffered article view counts to Postgres.
    FA: تسک دوره‌ای Celery برای انتقال دسته‌ای بازدیدهای بافرشده به دیتابیس.
    """
    return flush_buffered_article_view_counts()


@shared_task
def publish_scheduled_articles_task():
    """
    EN: Periodic Celery task to publish articles that are scheduled for the current time.
    FA: تسک دوره‌ای Celery برای انتشار مقاله‌هایی که برای زمان فعلی زمان‌بندی شده‌اند.
    """
    publish_scheduled_articles()


@shared_task(bind=True, max_retries=3, default_retry_delay=15)
def trigger_frontend_revalidation_task(self, paths=None, tags=None):
    """
    EN: Notifies Next.js ISR /api/revalidate endpoint to regenerate affected blog pages.
    FA: ارسال درخواست بازسازی کش (ISR) به اندپوینت Next.js برای صفحات مقاله مرتبط.
    """
    revalidate_url = (getattr(settings, "NEXT_REVALIDATE_URL", "") or "").strip()
    if not revalidate_url:
        return {"skipped": True, "reason": "NEXT_REVALIDATE_URL is not configured"}

    clean_paths = [str(p).strip() for p in (paths or []) if str(p or "").strip()]
    clean_tags = [str(t).strip() for t in (tags or []) if str(t or "").strip()]
    if not clean_paths and not clean_tags:
        return {"skipped": True, "reason": "No paths or tags provided"}

    headers = {"Content-Type": "application/json"}
    secret = (getattr(settings, "NEXT_REVALIDATION_SECRET", "") or "").strip()
    if secret:
        headers["x-revalidate-secret"] = secret

    payload = {}
    if clean_paths:
        payload["paths"] = clean_paths[:50]
    if clean_tags:
        payload["tags"] = clean_tags[:50]

    try:
        response = requests.post(revalidate_url, json=payload, headers=headers, timeout=5)
        if response.status_code >= 500:
            raise requests.HTTPError(
                f"Next.js revalidate HTTP {response.status_code}", response=response
            )
        if response.status_code >= 400:
            logger.warning(
                "Next.js revalidation rejected request",
                extra={"status_code": response.status_code, "body": response.text[:300]},
            )
            return {"ok": False, "status_code": response.status_code}
        return {"ok": True, "status_code": response.status_code}
    except requests.RequestException as exc:
        logger.warning(f"Next.js revalidation request failed, retrying: {exc}")
        raise self.retry(exc=exc)
