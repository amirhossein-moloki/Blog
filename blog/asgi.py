# blog/asgi.py

import os

# Channels-related imports are grouped here for better readability
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

# This line should be the first Django-related command
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blog.settings")

# !! Important: Call this function first so Django is configured
django_asgi_app = get_asgi_application()

# Now that Django is ready, we can import our routing
# import chat.routing
# import notifications.routing

# Finally, define the application using the variable we created
application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(
                # chat.routing.websocket_urlpatterns
                # + notifications.routing.websocket_urlpatterns
                []
            )
        ),
    }
)
