from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (CustomTokenObtainPairView, GoogleLoginView, UserViewSet)

router = DefaultRouter()
router.register(r"users", UserViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "auth/admin-login/",
        CustomTokenObtainPairView.as_view(),
        name="admin-login",
    ),
    path(
        "auth/google/login/",
        GoogleLoginView.as_view(),
        name="google-login",
    ),
]
