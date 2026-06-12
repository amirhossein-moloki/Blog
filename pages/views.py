from rest_framework import viewsets

from common.permissions import IsAdminUserOrReadOnly

from .models import Page
from .serializers import PageSerializer


class PageViewSet(viewsets.ModelViewSet):
    """
    EN:
    ViewSet for managing static pages.
    Provides read-only access to everyone and full access to administrators.

    FA:
    ViewSet برای مدیریت صفحات استاتیک.
    دسترسی فقط خواندنی برای همه و دسترسی کامل برای مدیران را فراهم می‌کند.
    """

    queryset = Page.objects.all()
    serializer_class = PageSerializer
    permission_classes = [IsAdminUserOrReadOnly]
