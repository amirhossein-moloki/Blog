from django import forms
from django.contrib import admin
from django.utils.html import format_html
from jalali_date.admin import ModelAdminJalaliMixin

from .models import Comment, Reaction


class CommentReplyInline(admin.TabularInline):
    """
    EN: Inline editor for nested comment replies.
    FA: ویرایشگر درون‌خطی برای پاسخ‌های تو در تو نظرات.
    """

    model = Comment
    fk_name = "parent"
    extra = 0
    raw_id_fields = ("user", "article")
    readonly_fields = ("created_at", "ip", "user_agent")
    fields = ("user", "content", "status", "created_at")


@admin.register(Comment)
class CommentAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    """
    EN:
    Comprehensive Admin interface for Comments.
    Includes moderation actions (approve, mark spam, remove), user/article autocomplete,
    and IP/user-agent auditing.

    FA:
    رابط کاربری جامع ادمین برای نظرات.
    شامل اکشن‌های نظارتی (تایید، اسپم، حذف)، تکمیل خودکار کاربر/مقاله و لاگ آی‌پی و یوزر ایجنت.
    """

    list_display = (
        "id",
        "user",
        "article",
        "short_content",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "user__email", "content", "ip")
    autocomplete_fields = ("user", "article", "parent")
    readonly_fields = ("ip", "user_agent", "created_at", "updated_at")
    inlines = [CommentReplyInline]
    actions = ["approve_comments", "mark_as_spam", "mark_as_removed"]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "article",
                    "user",
                    "parent",
                    "content",
                    "status",
                )
            },
        ),
        (
            "Audit & Metadata",
            {
                "classes": ("collapse",),
                "fields": ("ip", "user_agent", "created_at", "updated_at"),
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "article", "parent")

    @admin.display(description="Content Preview")
    def short_content(self, obj):
        if not obj.content:
            return ""
        clean_text = format_html("{}", obj.content)
        if len(clean_text) > 80:
            return f"{clean_text[:80]}..."
        return clean_text

    @admin.action(description="Approve selected comments")
    def approve_comments(self, request, queryset):
        updated = queryset.update(status="approved")
        self.message_user(request, f"{updated} comment(s) successfully approved.")

    @admin.action(description="Mark selected comments as Spam")
    def mark_as_spam(self, request, queryset):
        updated = queryset.update(status="spam")
        self.message_user(request, f"{updated} comment(s) marked as spam.")

    @admin.action(description="Mark selected comments as Removed")
    def mark_as_removed(self, request, queryset):
        updated = queryset.update(status="removed")
        self.message_user(request, f"{updated} comment(s) marked as removed.")


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    """
    EN: Admin interface for Reactions (likes, emojis) targeting Generic Content Types.
    FA: رابط کاربری ادمین برای واکنش‌ها (لایک‌ها، اموجی‌ها) که انواع محتوای عمومی را هدف قرار می‌دهند.
    """

    list_display = (
        "id",
        "user",
        "reaction",
        "content_type",
        "object_id",
        "content_object",
        "created_at",
    )
    list_filter = ("reaction", "content_type")
    search_fields = ("user__username", "reaction")
    autocomplete_fields = ("user",)
    readonly_fields = ("content_type", "object_id", "created_at")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "content_type")
