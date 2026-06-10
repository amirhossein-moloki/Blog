# Django Imports
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db import models

# 3rd-party Imports
from unfold.admin import ModelAdmin, TabularInline
from simple_history.admin import SimpleHistoryAdmin
from django_select2.forms import Select2Widget

# Local Imports
from .models import (
    User,
)

# --- ModelAdmins (Upgraded with Unfold and other features) ---

@admin.register(User)
class UserAdmin(BaseUserAdmin, SimpleHistoryAdmin, ModelAdmin):
    list_display = ("username", "email", "phone_number", "is_staff", "is_phone_verified")
    search_fields = ("username", "first_name", "last_name", "email", "phone_number")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups", "is_phone_verified")
    autocomplete_fields = ("groups",)
    readonly_fields = ("last_login", "date_joined")

    formfield_overrides = {
        models.ForeignKey: {"widget": Select2Widget},
    }

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email", "phone_number"), "classes": ("tab",)}),
        ("Profile", {"fields": ("profile_picture",), "classes": ("tab",)}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "is_phone_verified", "groups", "user_permissions"), "classes": ("tab",)}),
        ("Important dates", {"fields": ("last_login", "date_joined"), "classes": ("tab",)}),
    )
