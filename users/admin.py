# Django Imports
from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db import models
from django_select2.forms import Select2Widget
from simple_history.admin import SimpleHistoryAdmin

# 3rd-party Imports
from unfold.admin import ModelAdmin

# Local Imports
from .models import User

# --- Custom Forms ---


class UserAdminForm(forms.ModelForm):
    """
    Form for User model admin with custom validation or fields if needed.
    """

    class Meta:
        model = User
        fields = "__all__"


# --- ModelAdmins ---


@admin.register(User)
class UserAdmin(BaseUserAdmin, SimpleHistoryAdmin, ModelAdmin):
    """
    EN:
    Admin interface for the User model, enhanced with Unfold and SimpleHistory.
    Provides advanced filtering, searching, tabbed fieldsets, and bulk actions.

    FA:
    رابط کاربری ادمین برای مدل کاربر، تقویت شده با Unfold و SimpleHistory.
    قابلیت‌های فیلترینگ پیشرفته، جستجو و مجموعه‌فیلدهای تب‌بندی شده را فراهم می‌کند.
    """

    form = UserAdminForm
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "date_joined",
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
    actions = ["activate_users", "deactivate_users"]

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

    @admin.action(description="Activate selected users")
    def activate_users(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} user(s) successfully activated.")

    @admin.action(description="Deactivate selected users")
    def deactivate_users(self, request, queryset):
        # Safety check: prevent deactivating oneself
        if queryset.filter(id=request.user.id).exists():
            self.message_user(
                request,
                "You cannot deactivate your own account.",
                level="error",
            )
            return
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} user(s) successfully deactivated.")
