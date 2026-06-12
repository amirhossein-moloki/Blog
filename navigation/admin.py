from django.contrib import admin

from .models import Menu, MenuItem


class MenuItemInline(admin.TabularInline):
    """
    EN: Inline editor for Menu items within the Menu admin.
    FA: ویرایشگر داخلی برای آیتم‌های منو در ادمین منو.
    """

    model = MenuItem
    extra = 1


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    """
    EN: Admin interface for Menus, including an inline for menu items.
    FA: رابط کاربری ادمین برای منوها، شامل یک اینلاین برای آیتم‌های منو.
    """

    list_display = ("name", "location")
    list_filter = ("location",)
    inlines = [MenuItemInline]


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    """
    EN: Admin interface for individual Menu items.
    FA: رابط کاربری ادمین برای آیتم‌های منو به صورت تکی.
    """

    list_display = ("label", "menu", "url", "order")
    list_filter = ("menu",)
