from django.contrib import admin
from .models import Menu, MenuItem

class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 1

@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ('name', 'location')
    list_filter = ('location',)
    inlines = [MenuItemInline]

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('label', 'menu', 'url', 'order')
    list_filter = ('menu',)
