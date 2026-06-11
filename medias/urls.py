from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MediaViewSet, download_media

app_name = "medias"

router = DefaultRouter()
router.register(r"media", MediaViewSet, basename="media")

urlpatterns = [
    path("media/<int:media_id>/download/", download_media, name="download_media"),
    path("", include(router.urls)),
]
