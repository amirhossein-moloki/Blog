# Django Imports
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db import models
from django_select2.forms import Select2Widget
from simple_history.admin import SimpleHistoryAdmin

# 3rd-party Imports
from unfold.admin import ModelAdmin

# Local Imports
from .models import (
    User,
)

# --- ModelAdmins (Upgraded with Unfold and other features) ---


@admin.register(User)
class UserAdmin(BaseUserAdmin, SimpleHistoryAdmin, ModelAdmin):
    """
    EN:
    Admin interface for the User model, enhanced with Unfold and SimpleHistory.
    Provides advanced filtering, searching, and tabbed fieldsets.

    FA:
    رابط کاربری ادمین برای مدل کاربر، تقویت شده با Unfold و SimpleHistory.
    قابلیت‌های فیلترینگ پیشرفته، جستجو و مجموعه‌فیلدهای تب‌بندی شده را فراهم می‌کند.
    """

    list_display = (
        "username",
        "email",
        "is_staff",
    )
    search_fields = ("username", "first_name", "last_name", "email")
    list_filter = (
        "is_staff",
        "is_superuser",
        "is_active",
        "groups",
    )
    autocomplete_fields = ("groups",)
    readonly_fields = ("last_login", "date_joined")

    formfield_overrides = {
        models.ForeignKey: {"widget": Select2Widget},
    }

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Personal info",
            {
                "fields": ("first_name", "last_name", "email"),
                "classes": ("tab",),
            },
        ),
        ("Profile", {"fields": ("profile_picture",), "classes": ("tab",)}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
                "classes": ("tab",),
            },
        ),
        (
            "Important dates",
            {"fields": ("last_login", "date_joined"), "classes": ("tab",)},
        ),
    )
