from django.core.files.storage import default_storage
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from common.pagination import CustomPageNumberPagination
from users.permissions import IsOwnerOrAdmin

from .models import Media
from .serializers import MediaCreateSerializer, MediaDetailSerializer


class MediaViewSet(viewsets.ModelViewSet):
    """
    EN:
    ViewSet for managing media library.
    Allows authenticated users to upload files and owners/admins to edit/delete them.

    FA:
    ViewSet برای مدیریت کتابخانه رسانه.
    به کاربران احراز هویت شده اجازه آپلود فایل و به صاحبان/ادمین‌ها اجازه ویرایش/حذف آن‌ها را می‌دهد.
    """

    queryset = Media.objects.all().order_by("-created_at")
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrAdmin]
    pagination_class = CustomPageNumberPagination
    ordering = ["-created_at"]

    def get_queryset(self):
        """
        EN: Returns the queryset for media files with optimized related object fetching.
        FA: QuerySet فایل‌های رسانه را با واکشی بهینه اشیاء مرتبط بازمی‌گرداند.
        """
        return Media.objects.select_related("uploaded_by").all()

    def get_serializer_class(self):
        """
        EN: Returns the appropriate serializer class based on the action.
        FA: کلاس سریالایزر مناسب را بر اساس اکشن بازمی‌گرداند.
        """
        if self.action == "create":
            return MediaCreateSerializer
        return MediaDetailSerializer

    def create(self, request, *args, **kwargs):
        """
        EN: Handles media file upload and returns the detailed representation of the created object.
        FA: آپلود فایل رسانه را مدیریت کرده و نمایش جزئی شیء ایجاد شده را بازمی‌گرداند.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        detail_serializer = MediaDetailSerializer(instance)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)


def download_media(request, media_id):
    """
    EN: View function to download a media file by its ID.
    FA: تابع View برای دانلود یک فایل رسانه با استفاده از شناسه آن.
    """
    media = get_object_or_404(Media, pk=media_id)
    file = default_storage.open(media.storage_key, "rb")
    response = FileResponse(file, as_attachment=True, filename=media.title)
    return response
