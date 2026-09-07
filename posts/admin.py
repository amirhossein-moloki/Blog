# Django Imports
from django import forms
from django.contrib import admin, messages
from django.utils.html import format_html
from jalali_date.admin import ModelAdminJalaliMixin

# Local Imports
from medias.models import ArticleMedia

from .models import (
    Article,
    ArticleTag,
    ArticleTranslation,
    AuthorProfile,
    Category,
    GalleryItem,
    Podcast,
    PodcastCategory,
    Revision,
    Series,
    Tag,
)
from .services import validate_and_sanitize_blocks

# --- Custom Admin Forms ---


class ArticleTranslationForm(forms.ModelForm):
    """
    EN: Custom form for ArticleTranslation that validates JSON content_blocks via block engine.
    FA: فرم سفارشی برای ترجمه مقاله که ساختار JSON بلوک‌های محتوا را اعتبارسنجی می‌کند.
    """

    class Meta:
        model = ArticleTranslation
        fields = "__all__"

    def clean_content_blocks(self):
        blocks = self.cleaned_data.get("content_blocks")
        language_code = self.cleaned_data.get("language_code") or "en"
        if blocks:
            try:
                blocks = validate_and_sanitize_blocks(
                    blocks, language_code=language_code
                )
            except Exception as e:
                raise forms.ValidationError(f"Invalid content blocks: {e}")
        return blocks


# --- Admin Inlines ---


class ArticleTranslationInline(admin.StackedInline):
    """
    EN: Inline editor for Article translations with block engine validation.
    FA: ویرایشگر داخلی برای ترجمه‌های مقاله با اعتبارسنجی موتور بلوک‌ها.
    """

    model = ArticleTranslation
    form = ArticleTranslationForm
    extra = 1
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("reading_time_sec",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "language_code",
                    "title",
                    "slug",
                    "excerpt",
                    "short_description",
                    "content",
                    "content_blocks",
                    "reading_time_sec",
                )
            },
        ),
        (
            "SEO Settings",
            {
                "classes": ("collapse",),
                "fields": ("seo_title", "seo_description"),
            },
        ),
    )


class ArticleTagInline(admin.TabularInline):
    """
    EN: Inline editor for Article tags.
    FA: ویرایشگر داخلی برای برچسب‌های مقاله.
    """

    model = ArticleTag
    extra = 1
    autocomplete_fields = ("tag",)


class ArticleMediaInline(admin.TabularInline):
    """
    EN: Read-only inline viewer for Article media attachments.
    FA: نمایشگر داخلی و فقط-خواندنی برای پیوست‌های رسانه‌ای مقاله.
    """

    model = ArticleMedia
    readonly_fields = ("media", "attachment_type")
    extra = 0
    verbose_name = "Attachment"
    verbose_name_plural = "Attachments"

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# --- ModelAdmins ---


@admin.register(AuthorProfile)
class AuthorProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "user", "bio_excerpt")
    search_fields = ("display_name", "user__username", "user__email")
    autocomplete_fields = ("user", "avatar")

    @admin.display(description="Bio Excerpt")
    def bio_excerpt(self, obj):
        return obj.bio[:50] + "..." if obj.bio and len(obj.bio) > 50 else obj.bio


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "order", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("parent", "icon")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("parent", "icon")


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "description")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Series)
class SeriesAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "order_strategy")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Article)
class ArticleAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    """
    EN:
    Comprehensive Admin interface for Articles.
    Provides advanced fieldsets, N+1 optimized querysets, Jalali dates, and custom actions.

    FA:
    رابط کاربری جامع ادمین برای مقاله‌ها.
    مجموعه‌فیلدهای پیشرفته، کوئری‌های بهینه‌شده، تاریخ‌های جلالی و اکشن‌های سفارشی را فراهم می‌کند.
    """

    list_display = (
        "id",
        "get_title",
        "author",
        "category",
        "status",
        "visibility",
        "published_at",
        "is_hot",
        "views_count",
    )
    list_filter = ("status", "visibility", "category", "author", "is_hot")
    search_fields = (
        "translations__title",
        "translations__content",
        "translations__slug",
    )
    autocomplete_fields = (
        "author",
        "category",
        "series",
        "cover_image",
        "og_image",
    )
    filter_horizontal = ("related_articles",)
    inlines = [ArticleTranslationInline, ArticleTagInline, ArticleMediaInline]
    actions = [
        "make_published",
        "make_draft",
        "mark_as_hot",
        "clear_hot_status",
    ]

    fieldsets = (
        (None, {"fields": ("author",)}),
        ("Metadata & Taxonomy", {"fields": ("category", "series", "related_articles")}),
        ("Media", {"fields": ("cover_image", "og_image")}),
        (
            "Publishing & Visibility",
            {
                "fields": (
                    "status",
                    "visibility",
                    "published_at",
                    "scheduled_at",
                    "is_hot",
                )
            },
        ),
        (
            "SEO & System",
            {
                "classes": ("collapse",),
                "fields": ("canonical_url", "views_count"),
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("author", "category", "series", "cover_image")
            .prefetch_related("translations")
        )

    @admin.display(description="Title")
    def get_title(self, obj):
        translation = obj.translations.first()
        return translation.title if translation else f"Article #{obj.id}"

    @admin.action(description="Publish selected articles")
    def make_published(self, request, queryset):
        updated = queryset.update(status="published")
        self.message_user(
            request, f"{updated} article(s) successfully marked as published."
        )

    @admin.action(description="Set selected articles to Draft")
    def make_draft(self, request, queryset):
        updated = queryset.update(status="draft")
        self.message_user(request, f"{updated} article(s) set to draft status.")

    @admin.action(description="Mark selected articles as Hot")
    def mark_as_hot(self, request, queryset):
        updated = queryset.update(is_hot=True)
        self.message_user(request, f"{updated} article(s) marked as hot.")

    @admin.action(description="Clear Hot status for selected articles")
    def clear_hot_status(self, request, queryset):
        updated = queryset.update(is_hot=False)
        self.message_user(request, f"{updated} article(s) updated.")

    def save_model(self, request, obj, form, change):
        try:
            super().save_model(request, obj, form, change)
        except Exception as e:
            messages.set_level(request, messages.ERROR)
            self.message_user(
                request,
                f"An error occurred while saving the article: {e}",
                level=messages.ERROR,
            )


@admin.register(Revision)
class RevisionAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    """
    EN: Read-only Admin interface for Article Revisions.
    FA: رابط کاربری ادمین فقط-خواندنی برای بازنگری‌های مقاله.
    """

    list_display = ("id", "article", "editor", "language_code", "title", "created_at")
    list_filter = ("language_code", "editor")
    search_fields = ("title", "change_note")
    readonly_fields = (
        "article",
        "language_code",
        "editor",
        "content",
        "title",
        "excerpt",
        "change_note",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PodcastCategory)
class PodcastCategoryAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_active", "icon")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("icon",)


@admin.register(Podcast)
class PodcastAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    list_display = (
        "episode_number",
        "title",
        "category",
        "media_type",
        "published_date",
        "view_count",
        "is_active",
    )
    list_filter = ("category", "media_type", "is_active")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "slug", "description")
    autocomplete_fields = ("category", "cover_image", "audio_file", "video_file")
    filter_horizontal = ("related_podcasts",)
    fieldsets = (
        (
            None,
            {"fields": ("title", "slug", "category", "episode_number", "is_active")},
        ),
        (
            "Media & Content",
            {
                "fields": (
                    "cover_image",
                    "audio_file",
                    "media_type",
                    "video_file",
                    "video_url",
                    "description",
                    "duration",
                )
            },
        ),
        (
            "Statistics & Publishing",
            {"fields": ("published_date", "view_count", "related_podcasts")},
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("category", "cover_image")


@admin.register(GalleryItem)
class GalleryItemAdmin(admin.ModelAdmin):
    list_display = ("preview_image", "caption", "order", "is_active", "link")
    list_editable = ("order", "is_active")
    search_fields = ("caption",)
    autocomplete_fields = ("image",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("image")

    @admin.display(description="Image Preview")
    def preview_image(self, obj):
        if obj.image and obj.image.url:
            return format_html(
                '<img src="{}" style="max-height: 40px; max-width: 60px; object-fit: cover; border-radius: 4px;" />',
                obj.image.url,
            )
        return "N/A"
