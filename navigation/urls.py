from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MenuItemViewSet, MenuViewSet

app_name = "navigation"

router = DefaultRouter()
router.register(r"menus", MenuViewSet, basename="menu")
router.register(r"menu-items", MenuItemViewSet, basename="menu-item")

urlpatterns = [
    path("", include(router.urls)),
]
