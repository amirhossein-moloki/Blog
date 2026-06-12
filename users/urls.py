from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CustomTokenObtainPairView, GoogleLoginView, UserViewSet

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
    # EN: Social login endpoint using Google OAuth2.
    # FA: اندپوینت ورود از طریق شبکه‌های اجتماعی با استفاده از گوگل OAuth2.
    path(
        "auth/google/login/",
        GoogleLoginView.as_view(),
        name="google-login",
    ),
]
