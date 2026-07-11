from django.contrib import admin, messages
from jalali_date.admin import ModelAdminJalaliMixin

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


@admin.register(AuthorProfile)
class AuthorProfileAdmin(admin.ModelAdmin):
    """
    EN: Admin interface for AuthorProfile.
    FA: رابط کاربری ادمین برای پروفایل نویسنده.
    """

    list_display = ("display_name", "user")
    search_fields = ("display_name", "user__username")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    EN: Admin interface for Categories.
    FA: رابط کاربری ادمین برای دسته‌بندی‌ها.
    """

    list_display = ("name", "slug", "parent", "order", "icon")
    list_filter = ("parent",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """
    EN: Admin interface for Tags.
    FA: رابط کاربری ادمین برای برچسب‌ها.
    """

    list_display = ("name", "slug")
    search_fields = ("name",)


@admin.register(Series)
class SeriesAdmin(admin.ModelAdmin):
    """
    EN: Admin interface for Series.
    FA: رابط کاربری ادمین برای مجموعه‌ها.
    """

    list_display = ("title", "slug", "order_strategy")
    search_fields = ("title",)


class ArticleTranslationInline(admin.StackedInline):
    """
    EN: Inline editor for Article translations.
    FA: ویرایشگر داخلی برای ترجمه‌های مقاله.
    """

    model = ArticleTranslation
    extra = 1
    prepopulated_fields = {"slug": ("title",)}


class ArticleTagInline(admin.TabularInline):
    """
    EN: Inline editor for Article tags.
    FA: ویرایشگر داخلی برای برچسب‌های مقاله.
    """

    model = ArticleTag
    extra = 1


class ArticleMediaInline(admin.TabularInline):
    """
    EN: Inline viewer for Article media attachments.
    FA: نمایشگر داخلی برای پیوست‌های رسانه‌ای مقاله.
    """

    model = ArticleMedia
    readonly_fields = ("media", "attachment_type")
    extra = 0
    verbose_name = "Attachment"
    verbose_name_plural = "Attachments"

    def has_add_permission(self, request, obj=None):
        """
        EN: Disables adding attachments directly from the article admin.
        FA: اضافه کردن مستقیم پیوست‌ها از پنل ادمین مقاله را غیرفعال می‌کند.
        """
        return False

    def has_delete_permission(self, request, obj=None):
        """
        EN: Disables deleting attachments directly from the article admin.
        FA: حذف مستقیم پیوست‌ها از پنل ادمین مقاله را غیرفعال می‌کند.
        """
        return False


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    """
    EN:
    Comprehensive Admin interface for Articles.
    Provides advanced fieldsets, inlines for translations, tags and media, and custom save logic.

    FA:
    رابط کاربری جامع ادمین برای مقاله‌ها.
    مجموعه‌فیلدهای پیشرفته، اینلاین‌ها برای ترجمه‌ها، برچسب‌ها و رسانه‌ها و منطق ذخیره‌سازی سفارشی را فراهم می‌کند.
    """

    list_display = (
        "id",
        "author",
        "category",
        "status",
        "published_at",
        "is_hot",
    )
    list_filter = ("status", "visibility", "category", "author", "is_hot")
    search_fields = ("translations__title", "translations__content")
    autocomplete_fields = ("cover_image", "og_image")
    filter_horizontal = ("related_articles",)
    inlines = [ArticleTranslationInline, ArticleTagInline, ArticleMediaInline]
    fieldsets = (
        (None, {"fields": ("author",)}),
        ("Metadata", {"fields": ("category", "series", "related_articles")}),
        ("Media", {"fields": ("cover_image", "og_image")}),
        (
            "Status & Visibility",
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
            "Other",
            {
                "classes": ("collapse",),
                "fields": ("canonical_url",),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        """
        EN: Overrides save_model to catch and display errors in the admin UI.
        FA: متد save_model را برای دریافت و نمایش خطاها در رابط کاربری ادمین بازنویسی می‌کند.
        """
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
    EN: Admin interface for Article Revisions.
    FA: رابط کاربری ادمین برای بازنگری‌های مقاله.
    """

    list_display = ("article", "editor", "created_at")
    list_filter = ("editor",)
    search_fields = ("article__id",)


@admin.register(PodcastCategory)
class PodcastCategoryAdmin(admin.ModelAdmin):
    """
    EN: Admin interface for Podcast Categories.
    FA: رابط کاربری ادمین برای دسته‌بندی‌های پادکست.
    """

    list_display = ("title", "slug", "is_active", "icon")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Podcast)
class PodcastAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    """
    EN: Admin interface for Podcasts.
    FA: رابط کاربری ادمین برای پادکست‌ها.
    """

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
            "Statistics & Dates",
            {"fields": ("published_date", "view_count", "related_podcasts")},
        ),
    )


@admin.register(GalleryItem)
class GalleryItemAdmin(admin.ModelAdmin):
    """
    EN: Admin interface for Gallery Items.
    FA: رابط کاربری ادمین برای گالری تصاویر.
    """

    list_display = ("caption", "order", "is_active", "link")
    list_editable = ("order", "is_active")
    search_fields = ("caption",)
