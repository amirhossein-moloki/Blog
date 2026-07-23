"""
EN: Project root package init. Ensures Celery app is loaded on startup.
FA: پکیج روت پروژه. اطمینان از بارگذاری برنامه Celery در زمان شروع به کار.
"""

from .celery import app as celery_app

__all__ = ("celery_app",)
