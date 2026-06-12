from django.contrib import admin
from jalali_date.admin import ModelAdminJalaliMixin

from .forms import PageAdminForm
from .models import Page


@admin.register(Page)
class PageAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    """
    EN: Admin interface for static Pages, with Jalali date and CKEditor support.
    FA: رابط کاربری ادمین برای صفحات استاتیک، با پشتیبانی از تاریخ جلالی و CKEditor.
    """

    form = PageAdminForm
    list_display = ("title", "slug", "status", "published_at")
    list_filter = ("status",)
    search_fields = ("title", "content")
