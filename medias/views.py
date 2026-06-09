from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage

from common.pagination import CustomPageNumberPagination
from users.permissions import IsOwnerOrAdmin
from .models import Media
from .serializers import MediaDetailSerializer, MediaCreateSerializer

class MediaViewSet(viewsets.ModelViewSet):
    queryset = Media.objects.all().order_by('-created_at')
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrAdmin]
    pagination_class = CustomPageNumberPagination
    ordering = ['-created_at']

    def get_queryset(self):
        return Media.objects.select_related('uploaded_by').all()

    def get_serializer_class(self):
        if self.action == 'create':
            return MediaCreateSerializer
        return MediaDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        detail_serializer = MediaDetailSerializer(instance)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)

def download_media(request, media_id):
    media = get_object_or_404(Media, pk=media_id)
    file = default_storage.open(media.storage_key, 'rb')
    response = FileResponse(file, as_attachment=True, filename=media.title)
    return response
