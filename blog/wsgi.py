"""
WSGI config for blog project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# EN: Set the default settings module for the WSGI application.
# FA: تنظیم ماژول تنظیمات پیش‌فرض برای اپلیکیشن WSGI.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blog.settings")

# EN: Main application entry point for WSGI-compatible web servers.
# FA: نقطه ورود اصلی اپلیکیشن برای وب‌سرورهای سازگار با WSGI.
application = get_wsgi_application()
