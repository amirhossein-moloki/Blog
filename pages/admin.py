from django.contrib import admin
from jalali_date.admin import ModelAdminJalaliMixin

from .forms import PageAdminForm
from .models import Page


@admin.register(Page)
class PageAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    form = PageAdminForm
    list_display = ("title", "slug", "status", "published_at")
    list_filter = ("status",)
    search_fields = ("title", "content")
