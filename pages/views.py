"""
EN: Views for managing static pages with long-term Level 4 caching.
FA: نماها برای مدیریت صفحات استاتیک با قابلیت کش طولانی‌مدت سطح ۴.
"""

from rest_framework import viewsets
from rest_framework.response import Response

from common.cache import build_cache_key, cache_manager
from common.permissions import IsAdminUserOrReadOnly

from .models import Page
from .serializers import PageSerializer


class PageViewSet(viewsets.ModelViewSet):
    """
    EN:
    ViewSet for managing static pages.
    Provides read-only access to everyone and full access to administrators with Level 4 caching.

    FA:
    ViewSet برای مدیریت صفحات استاتیک.
    دسترسی فقط خواندنی برای همه و دسترسی کامل برای مدیران را به همراه کشینگ سطح ۴ فراهم می‌کند.
    """

    queryset = Page.objects.all()
    serializer_class = PageSerializer
    permission_classes = [IsAdminUserOrReadOnly]

    def retrieve(self, request, *args, **kwargs):
        """
        EN: Retrieves a page with Level 4 (Long Cache).
        FA: دریافت جزئیات صفحه استاتیک با کش طولانی‌مدت.
        """
        slug = kwargs.get("slug") or kwargs.get("pk")
        cache_key = build_cache_key("pages", "page_detail", str(slug))

        def rebuild():
            obj = self.get_object()
            serializer = self.get_serializer(obj)
            return serializer.data

        data = cache_manager.get_or_create(
            key=cache_key,
            rebuild_callback=rebuild,
            group="pages",
            tags=[f"page:{slug}"],
            soft_ttl_sec=86400,
            hard_ttl_sec=604800,
        )
        return Response(data)
