from rest_framework import serializers

from .models import Menu, MenuItem


class MenuItemSerializer(serializers.ModelSerializer):
    """
    EN: Serializer for Menu items, including all their fields.
    FA: سریالایزر برای آیتم‌های منو، شامل تمامی فیلدها.
    """

    class Meta:
        model = MenuItem
        fields = "__all__"


class MenuSerializer(serializers.ModelSerializer):
    """
    EN: Serializer for Menus, including nested MenuItem representations.
    FA: سریالایزر برای منوها، شامل نمایش آیتم‌های منوی تو در تو.
    """

    items = MenuItemSerializer(many=True, read_only=True)

    class Meta:
        model = Menu
        fields = "__all__"
