from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import UserViewSet

# EN: Standard DRF router for User management endpoints.
# FA: روتر استاندارد DRF برای اندپوینت‌های مدیریت کاربران.
router = DefaultRouter()
router.register(r"users", UserViewSet)

urlpatterns = [
    # --- App URLs ---
    path("", include(router.urls)),
]
