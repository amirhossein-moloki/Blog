# Django Imports
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from jalali_date import datetime2jalali
from jalali_date.admin import ModelAdminJalaliMixin

# Local Imports
from .forms import MediaAdminForm
from .models import Media, MediaVariant
from .services import create_media_from_file


class MediaVariantInline(admin.TabularInline):
    """
    EN: Read-only inline display for MediaVariants.
    FA: نمایش درون‌خطی و فقط-خواندنی برای نسخه‌های پردازش‌شده رسانه.
    """

    model = MediaVariant
    extra = 0
    can_delete = False
    readonly_fields = (
        "variant_name",
        "format",
        "width",
        "height",
        "size_bytes",
        "storage_key",
        "url",
    )

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Media)
class MediaAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    """
    EN:
    Comprehensive Admin configuration for Media objects.
    Provides image preview thumbnails, Jalali date integration, status moderation,
    and safe storage metadata handling.

    FA:
    تنظیمات جامع ادمین برای اشیاء رسانه.
    پیش‌نمایش تصویر، تاریخ جلالی، نظارت بر وضعیت و مدیریت امن متادیتا را فراهم می‌کند.
    """

    form = MediaAdminForm
    inlines = [MediaVariantInline]
    list_display = (
        "preview_thumbnail",
        "title",
        "type",
        "mime",
        "size_bytes",
        "status",
        "uploaded_by",
        "get_created_at_jalali",
        "download_link",
    )
    list_filter = ("status", "type", "mime", "is_deleted")
    search_fields = ("title", "alt_text", "storage_key", "content_hash")
    readonly_fields = (
        "storage_key",
        "url",
        "type",
        "mime",
        "width",
        "height",
        "duration",
        "size_bytes",
        "content_hash",
        "checksum_algorithm",
        "uploaded_by",
        "preview_thumbnail_large",
        "get_created_at_jalali",
        "download_link",
    )
    actions = ["quarantine_media", "mark_as_ready", "soft_delete_media"]

    fieldsets = (
        (None, {"fields": ("title", "alt_text", "status", "is_deleted")}),
        ("Preview", {"fields": ("preview_thumbnail_large", "download_link")}),
        (
            "File Metadata",
            {
                "fields": (
                    "type",
                    "mime",
                    "size_bytes",
                    "width",
                    "height",
                    "duration",
                )
            },
        ),
        (
            "System & Storage",
            {
                "classes": ("collapse",),
                "fields": (
                    "storage_key",
                    "url",
                    "content_hash",
                    "checksum_algorithm",
                    "uploaded_by",
                    "get_created_at_jalali",
                ),
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("uploaded_by")

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields
        return (
            "storage_key",
            "url",
            "type",
            "mime",
            "width",
            "height",
            "duration",
            "size_bytes",
            "content_hash",
            "checksum_algorithm",
            "uploaded_by",
            "preview_thumbnail_large",
            "get_created_at_jalali",
            "download_link",
        )

    @admin.display(description="Thumbnail")
    def preview_thumbnail(self, obj):
        if obj.type == "image" and obj.url:
            return format_html(
                '<img src="{}" style="max-height: 40px; max-width: 60px; object-fit: cover; border-radius: 4px;" />',
                obj.url,
            )
        return "N/A"

    @admin.display(description="Image Preview")
    def preview_thumbnail_large(self, obj):
        if obj.type == "image" and obj.url:
            return format_html(
                '<img src="{}" style="max-height: 250px; max-width: 400px; object-fit: contain; border-radius: 6px; border: 1px solid #ccc;" />',
                obj.url,
            )
        return "No visual preview available"

    @admin.display(description="Created At (Jalali)", ordering="created_at")
    def get_created_at_jalali(self, obj):
        if obj.created_at:
            return datetime2jalali(obj.created_at).strftime("%Y-%m-%d %H:%M:%S")
        return None

    @admin.display(description="Download")
    def download_link(self, obj):
        if obj.pk:
            download_url = reverse("medias:download_media", args=[obj.pk])
            return format_html(
                '<a href="{}" class="button" target="_blank">Download File</a>',
                download_url,
            )
        return "N/A"

    @admin.action(description="Quarantine selected media items")
    def quarantine_media(self, request, queryset):
        updated = queryset.update(status="Quarantined")
        self.message_user(
            request, f"{updated} media item(s) moved to Quarantined status."
        )

    @admin.action(description="Mark selected media as Ready")
    def mark_as_ready(self, request, queryset):
        updated = queryset.update(status="Ready")
        self.message_user(request, f"{updated} media item(s) marked as Ready.")

    @admin.action(description="Soft delete selected media items")
    def soft_delete_media(self, request, queryset):
        updated = queryset.update(is_deleted=True)
        self.message_user(request, f"{updated} media item(s) soft-deleted.")

    def save_model(self, request, obj, form, change):
        uploaded_file = form.cleaned_data.get("file")
        if uploaded_file:
            new_media = create_media_from_file(
                uploaded_file,
                request.user,
                alt_text=form.cleaned_data.get("alt_text", ""),
                title=form.cleaned_data.get("title", ""),
            )
            obj.storage_key = new_media.storage_key
            obj.url = new_media.url
            obj.type = new_media.type
            obj.mime = new_media.mime
            obj.size_bytes = new_media.size_bytes
            obj.title = new_media.title
            obj.width = new_media.width
            obj.height = new_media.height
            obj.duration = new_media.duration
            obj.content_hash = new_media.content_hash
            obj.status = new_media.status
            new_media.delete()

        if not obj.pk and not obj.uploaded_by_id:
            obj.uploaded_by = request.user

        super().save_model(request, obj, form, change)
