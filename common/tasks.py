"""
EN: Imports and exposes common cache tasks and automated backup/restore validation tasks with distributed locking.
FA: ایمپورت و ارائه تسک‌های کش و تسک‌های پشتیبان‌گیری خودکار/اعتبارسنجی بازیابی با قفل‌های توزیع‌شده.
"""

import logging

from celery import shared_task
from django.core.cache import cache
from django.core.management import call_command

from common.cache.locks import DistributedLock

from .cache.tasks import (
    warmup_article_detail,
    warmup_category_pages,
    warmup_homepage,
    warmup_related_content,
)

logger = logging.getLogger(__name__)


def get_redis_client():
    """
    Attempts to retrieve the raw Redis client from the Django cache backend if active.
    """
    try:
        return cache.client.get_client()
    except Exception:
        return None


@shared_task
def backup_database_task():
    """
    Celery task to run the database backup management command with distributed lock protection.
    """
    redis_client = get_redis_client()
    lock = DistributedLock(redis_client, "backup_database_lock")

    # Non-blocking lock, fails fast with timeout_sec=0 if another instance is already backing up
    if not lock.acquire(expire_sec=1800, timeout_sec=0):
        logger.warning(
            "Database backup task skipped: another backup process is actively running."
        )
        return False

    logger.info("Starting automated Celery database backup...")
    try:
        call_command("backup_database")
        logger.info("Automated Celery database backup finished successfully.")
        return True
    except Exception as e:
        logger.error(f"Automated Celery database backup failed: {str(e)}")
        raise e
    finally:
        lock.release()


@shared_task
def backup_media_task():
    """
    Celery task to run the media incremental sync backup management command with distributed lock protection.
    """
    redis_client = get_redis_client()
    lock = DistributedLock(redis_client, "backup_media_lock")

    if not lock.acquire(expire_sec=1800, timeout_sec=0):
        logger.warning(
            "Media backup task skipped: another media sync process is actively running."
        )
        return False

    logger.info("Starting automated Celery media sync backup...")
    try:
        call_command("backup_media")
        logger.info("Automated Celery media sync backup finished successfully.")
        return True
    except Exception as e:
        logger.error(f"Automated Celery media sync backup failed: {str(e)}")
        raise e
    finally:
        lock.release()


@shared_task
def backup_config_task():
    """
    Celery task to run the configuration backup management command with distributed lock protection.
    """
    redis_client = get_redis_client()
    lock = DistributedLock(redis_client, "backup_config_lock")

    if not lock.acquire(expire_sec=600, timeout_sec=0):
        logger.warning(
            "Configuration backup task skipped: another configuration backup is actively running."
        )
        return False

    logger.info("Starting automated Celery config backup...")
    try:
        call_command("backup_config")
        logger.info("Automated Celery config backup finished successfully.")
        return True
    except Exception as e:
        logger.error(f"Automated Celery config backup failed: {str(e)}")
        raise e
    finally:
        lock.release()


@shared_task
def validate_backups_task():
    """
    Celery task to run the restore_system command in validation/discovery mode (Weekly Verification) with locking.
    """
    redis_client = get_redis_client()
    lock = DistributedLock(redis_client, "validate_backups_lock")

    if not lock.acquire(expire_sec=1800, timeout_sec=0):
        logger.warning(
            "Weekly backup validation task skipped: another validation process is active."
        )
        return False

    logger.info("Starting automated weekly backup validation...")
    try:
        call_command("restore_system")
        logger.info("Automated weekly backup validation completed successfully.")
        return True
    except Exception as e:
        logger.error(f"Automated weekly backup validation failed: {str(e)}")
        raise e
    finally:
        lock.release()


__all__ = [
    "warmup_homepage",
    "warmup_article_detail",
    "warmup_category_pages",
    "warmup_related_content",
    "backup_database_task",
    "backup_media_task",
    "backup_config_task",
    "validate_backups_task",
]
