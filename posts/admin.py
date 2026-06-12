from django.contrib import admin, messages
from jalali_date.admin import ModelAdminJalaliMixin

from medias.models import PostMedia

from .forms import PostAdminForm
from .models import AuthorProfile, Category, Post, PostTag, Revision, Series, Tag


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

    list_display = ("name", "slug", "parent", "order")
    list_filter = ("parent",)
    search_fields = ("name",)


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


class PostTagInline(admin.TabularInline):
    """
    EN: Inline editor for Post tags.
    FA: ویرایشگر داخلی برای برچسب‌های پست.
    """

    model = PostTag
    extra = 1


class PostMediaInline(admin.TabularInline):
    """
    EN: Inline viewer for Post media attachments.
    FA: نمایشگر داخلی برای پیوست‌های رسانه‌ای پست.
    """

    model = PostMedia
    readonly_fields = ("media", "attachment_type")
    extra = 0
    verbose_name = "Attachment"
    verbose_name_plural = "Attachments"

    def has_add_permission(self, request, obj=None):
        """
        EN: Disables adding attachments directly from the post admin.
        FA: اضافه کردن مستقیم پیوست‌ها از پنل ادمین پست را غیرفعال می‌کند.
        """
        return False

    def has_delete_permission(self, request, obj=None):
        """
        EN: Disables deleting attachments directly from the post admin.
        FA: حذف مستقیم پیوست‌ها از پنل ادمین پست را غیرفعال می‌کند.
        """
        return False


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    """
    EN:
    Comprehensive Admin interface for Posts.
    Provides advanced fieldsets, inlines for tags and media, and custom save logic.

    FA:
    رابط کاربری جامع ادمین برای پست‌ها.
    مجموعه‌فیلدهای پیشرفته، اینلاین‌ها برای برچسب‌ها و رسانه‌ها و منطق ذخیره‌سازی سفارشی را فراهم می‌کند.
    """

    form = PostAdminForm
    list_display = (
        "title",
        "slug",
        "author",
        "category",
        "status",
        "published_at",
        "is_hot",
    )
    list_filter = ("status", "visibility", "category", "author", "is_hot")
    search_fields = ("title", "content")
    autocomplete_fields = ("cover_media", "og_image")
    inlines = [PostTagInline, PostMediaInline]
    fieldsets = (
        (None, {"fields": ("title", "slug", "author", "content", "excerpt")}),
        ("Metadata", {"fields": ("category", "series")}),
        ("Media", {"fields": ("cover_media", "og_image")}),
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
            "SEO",
            {
                "classes": ("collapse",),
                "fields": ("seo_title", "seo_description", "canonical_url"),
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
                f"An error occurred while saving the post: {e}",
                level=messages.ERROR,
            )


@admin.register(Revision)
class RevisionAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    """
    EN: Admin interface for Post Revisions.
    FA: رابط کاربری ادمین برای بازنگری‌های پست.
    """

    list_display = ("post", "editor", "created_at")
    list_filter = ("editor",)
    search_fields = ("post__title",)
