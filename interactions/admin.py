from django.contrib import admin
from jalali_date.admin import ModelAdminJalaliMixin

from .models import Comment, Reaction


@admin.register(Comment)
class CommentAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    """
    EN: Admin interface for Comments, using Jalali date support.
    FA: رابط کاربری ادمین برای نظرات، با پشتیبانی از تاریخ جلالی.
    """

    list_display = ("user", "post", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("user__username", "content")


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    """
    EN: Admin interface for Reactions (likes, emojis).
    FA: رابط کاربری ادمین برای واکنش‌ها (لایک‌ها، اموجی‌ها).
    """

    list_display = ("user", "reaction", "content_object", "created_at")
    list_filter = ("reaction",)
