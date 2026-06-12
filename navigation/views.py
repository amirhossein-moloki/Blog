from rest_framework import viewsets

from common.permissions import IsAdminUserOrReadOnly

from .models import Menu, MenuItem
from .serializers import MenuItemSerializer, MenuSerializer


class MenuViewSet(viewsets.ModelViewSet):
    """
    EN:
    ViewSet for managing navigation menus.
    Provides read-only access to everyone and full access to administrators.

    FA:
    ViewSet برای مدیریت منوهای پیمایش.
    دسترسی فقط خواندنی برای همه و دسترسی کامل برای مدیران را فراهم می‌کند.
    """

    queryset = Menu.objects.all()
    serializer_class = MenuSerializer
    permission_classes = [IsAdminUserOrReadOnly]


class MenuItemViewSet(viewsets.ModelViewSet):
    """
    EN:
    ViewSet for managing individual menu items.
    Allows administrative control over links and their hierarchy.

    FA:
    ViewSet برای مدیریت آیتم‌های منو به صورت تکی.
    اجازه کنترل مدیریتی روی لینک‌ها و سلسله‌مراتب آن‌ها را می‌دهد.
    """

    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    permission_classes = [IsAdminUserOrReadOnly]
