import os

from celery import Celery

# EN: Set the default Django settings module for the 'celery' program.
# FA: تنظیم ماژول تنظیمات پیش‌فرض جنگو برای برنامه 'celery'.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blog.settings")

app = Celery("blog")

# EN: Using a string here means the worker doesn't have to serialize
# EN: the configuration object to child processes.
# EN: - namespace='CELERY' means all celery-related configuration keys should have a `CELERY_` prefix.
# FA: استفاده از رشته در اینجا به این معنی است که worker مجبور نیست شیء تنظیمات را برای فرآیندهای فرزند سریال‌سازی کند.
# FA: - عبارت namespace='CELERY' به این معنی است که تمامی کلیدهای تنظیمات مرتبط با celery باید پیشوند `CELERY_` داشته باشند.
app.config_from_object("django.conf:settings", namespace="CELERY")

# EN: Load task modules from all registered Django app configs.
# FA: بارگذاری ماژول‌های تسک از تمامی تنظیمات اپلیکیشن‌های ثبت شده در جنگو.
app.autodiscover_tasks()
