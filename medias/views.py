from django.core.files.storage import default_storage
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.pagination import CustomPageNumberPagination
from common.permissions import IsAuthorOrAdmin

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
    permission_classes = [IsAuthorOrAdmin]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        """
        EN: Returns the queryset for media files with optimized related object fetching,
        supporting comprehensive search, filters, and sorting.
        FA: QuerySet فایل‌های رسانه را با واکشی بهینه اشیاء مرتبط، به همراه فیلترها و مرتب‌سازی بازمی‌گرداند.
        """
        queryset = Media.objects.select_related("uploaded_by").prefetch_related("variants").all()

        # Exclude soft-deleted media by default unless requested (e.g. including deleted)
        include_deleted = self.request.query_params.get("include_deleted", "false").lower() in ("true", "1")
        if not include_deleted:
            queryset = queryset.filter(is_deleted=False)

        # 1. Search filter: ?q=architecture
        q = self.request.query_params.get("q")
        if q:
            from django.db.models import Q
            queryset = queryset.filter(Q(title__icontains=q) | Q(alt_text__icontains=q))

        # 2. Type filter: ?type=image
        media_type = self.request.query_params.get("type")
        if media_type:
            queryset = queryset.filter(type=media_type)

        # 3. Mime filter: ?mime=image/jpeg
        mime = self.request.query_params.get("mime")
        if mime:
            queryset = queryset.filter(mime=mime)

        # 4. Uploaded by: ?uploaded_by=user_id
        uploaded_by = self.request.query_params.get("uploaded_by")
        if uploaded_by:
            queryset = queryset.filter(uploaded_by_id=uploaded_by)

        # 5. Date ranges: created_after / created_before
        created_after = self.request.query_params.get("created_after")
        if created_after:
            queryset = queryset.filter(created_at__date__gte=created_after)

        created_before = self.request.query_params.get("created_before")
        if created_before:
            queryset = queryset.filter(created_at__date__lte=created_before)

        # 6. Sorting: ?ordering=-created_at, size, title
        ordering = self.request.query_params.get("ordering") or "-created_at"
        # Map requested order fields
        order_fields = []
        for term in ordering.split(","):
            term = term.strip()
            if term == "size":
                order_fields.append("size_bytes")
            elif term == "-size":
                order_fields.append("-size_bytes")
            else:
                order_fields.append(term)

        queryset = queryset.order_by(*order_fields)
        return queryset

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
        EN: Handles media file upload, duplicate check, and returns the detailed representation.
        FA: آپلود فایل رسانه را مدیریت کرده، فایل‌های تکراری را شناسایی کرده و نمایش جزئیات را بازمی‌گرداند.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        if getattr(instance, "is_duplicate", False):
            # Return duplicate response structure exactly as requested
            return Response({
                "duplicate": True,
                "existing_media_id": instance.existing_media_id,
                "id": instance.id,
                "url": instance.url,
                "title": instance.title,
                "metadata": {
                    "width": instance.width,
                    "height": instance.height,
                    "mime": instance.mime,
                    "size": instance.size_bytes,
                },
                "variants": {
                    v.variant_name: v.url for v in instance.variants.all()
                }
            }, status=status.HTTP_200_OK)

        detail_serializer = MediaDetailSerializer(instance, context={"request": request})
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """
        EN: Safely deletes a media file, blocking deletion if actively used unless force override is passed.
        FA: فایل رسانه را با امنیت بالا حذف می‌کند؛ در صورتی که فایل فعال باشد از حذف آن جلوگیری می‌شود مگر با اعمال force.
        """
        media = self.get_object()
        force = request.query_params.get("force", "false").lower() in ("true", "1")

        # Check references/usage
        from .services import MediaUsageService, MediaDeletionService
        usage = MediaUsageService.get_usage(media)
        if usage["usage_count"] > 0 and not force:
            return Response({
                "error": "MEDIA_IN_USE",
                "message": "This media is currently used by published content.",
                "usage_count": usage["usage_count"],
                "references": usage["references"]
            }, status=status.HTTP_400_BAD_REQUEST)

        # Deletion behavior: soft delete by default
        MediaDeletionService.soft_delete(media)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        """
        EN: Restores a soft-deleted media file.
        FA: یک رسانه حذف شده به صورت نرم را بازیابی می‌کند.
        """
        media = get_object_or_404(Media, pk=pk)
        from .services import MediaDeletionService
        MediaDeletionService.restore(media)
        return Response({"status": "restored"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def purge(self, request, pk=None):
        """
        EN: Permanently deletes physical files and database record.
        FA: به طور فیزیکی و همیشگی فایل و رکورد دیتابیس را حذف می‌کند.
        """
        media = get_object_or_404(Media, pk=pk)
        from .services import MediaDeletionService
        MediaDeletionService.hard_delete(media)
        return Response({"status": "permanently_deleted"}, status=status.HTTP_204_NO_CONTENT)


def download_media(request, media_id):
    """
    EN: View function to download a media file by its ID.
    FA: تابع View برای دانلود یک فایل رسانه با استفاده از شناسه آن.
    """
    media = get_object_or_404(Media, pk=media_id)
    file = default_storage.open(media.storage_key, "rb")
    response = FileResponse(file, as_attachment=True, filename=media.title)
    return response
