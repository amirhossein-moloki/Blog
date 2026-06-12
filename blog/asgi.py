# blog/asgi.py

import os

# EN: Channels-related imports for handling asynchronous protocols like WebSockets.
# FA: وارد کردن موارد مرتبط با Channels برای مدیریت پروتکل‌های نامتقارن مانند WebSocket.
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

# EN: This line sets the default settings module for the ASGI application.
# FA: این خط ماژول تنظیمات پیش‌فرض را برای اپلیکیشن ASGI تنظیم می‌کند.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blog.settings")

# EN: !! Important: Call this function first so Django is properly configured before routing.
# FA: !! مهم: این تابع را ابتدا فراخوانی کنید تا جنگو قبل از مسیریابی به درستی پیکربندی شود.
django_asgi_app = get_asgi_application()

# EN: Standard protocol router for handling HTTP and WebSocket connections.
# FA: روتر استاندارد پروتکل برای مدیریت اتصالات HTTP و WebSocket.
application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(
                # EN: Placeholder for future WebSocket routing.
                # FA: جایگزین برای مسیریابی WebSocket در آینده.
                []
            )
        ),
    }
)
