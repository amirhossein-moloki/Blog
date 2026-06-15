from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CustomTokenObtainPairView, UserViewSet

# EN: Standard DRF router for User management endpoints.
# FA: روتر استاندارد DRF برای اندپوینت‌های مدیریت کاربران.
router = DefaultRouter()
router.register(r"users", UserViewSet)

urlpatterns = [
    path("", include(router.urls)),
    # EN: Specialized login endpoint for administrative access.
    # FA: اندپوینت اختصاصی ورود برای دسترسی‌های مدیریتی.
    path(
        "auth/admin-login/",
        CustomTokenObtainPairView.as_view(),
        name="admin-login",
    ),
]
