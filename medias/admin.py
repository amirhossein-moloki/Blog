from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from jalali_date import datetime2jalali
from jalali_date.admin import ModelAdminJalaliMixin

from .forms import MediaAdminForm
from .models import Media
from .services import create_media_from_file


@admin.register(Media)
class MediaAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    form = MediaAdminForm
    list_display = (
        "title",
        "type",
        "mime",
        "size_bytes",
        "get_created_at_jalali",
        "download_link",
    )
    list_filter = ("type", "mime")
    search_fields = ("title", "alt_text")
    readonly_fields = (
        "storage_key",
        "url",
        "type",
        "mime",
        "size_bytes",
        "uploaded_by",
        "get_created_at_jalali",
        "download_link",
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields
        return (
            "storage_key",
            "url",
            "type",
            "mime",
            "size_bytes",
            "uploaded_by",
            "download_link",
        )

    @admin.display(description="Created At (Jalali)", ordering="created_at")
    def get_created_at_jalali(self, obj):
        if obj.created_at:
            return datetime2jalali(obj.created_at).strftime("%Y-%m-%d %H:%M:%S")
        return None

    def download_link(self, obj):
        if obj.pk:
            download_url = reverse("medias:download_media", args=[obj.pk])
            return format_html('<a href="{}">Download</a>', download_url)
        return "N/A"

    download_link.short_description = "Download"

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
            new_media.delete()

        if not obj.pk:
            obj.uploaded_by = request.user

        super().save_model(request, obj, form, change)
