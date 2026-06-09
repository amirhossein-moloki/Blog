from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html
from jalali_date.admin import ModelAdminJalaliMixin
from .models import (
    AuthorProfile, Category, Tag, Post, PostTag, Series, Revision
)
from medias.models import PostMedia
from .forms import PostAdminForm

@admin.register(AuthorProfile)
class AuthorProfileAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'user')
    search_fields = ('display_name', 'user__username')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'order')
    list_filter = ('parent',)
    search_fields = ('name',)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)

@admin.register(Series)
class SeriesAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'order_strategy')
    search_fields = ('title',)

class PostTagInline(admin.TabularInline):
    model = PostTag
    extra = 1

class PostMediaInline(admin.TabularInline):
    model = PostMedia
    readonly_fields = ('media', 'attachment_type')
    extra = 0
    verbose_name = 'Attachment'
    verbose_name_plural = 'Attachments'

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    form = PostAdminForm
    list_display = ('title', 'slug', 'author', 'category', 'status', 'published_at', 'is_hot')
    list_filter = ('status', 'visibility', 'category', 'author', 'is_hot')
    search_fields = ('title', 'content')
    autocomplete_fields = ('cover_media', 'og_image')
    inlines = [PostTagInline, PostMediaInline]
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'author', 'content', 'excerpt')
        }),
        ('Metadata', {
            'fields': ('category', 'series')
        }),
        ('Media', {
            'fields': ('cover_media', 'og_image')
        }),
        ('Status & Visibility', {
            'fields': ('status', 'visibility', 'published_at', 'scheduled_at', 'is_hot')
        }),
        ('SEO', {
            'classes': ('collapse',),
            'fields': ('seo_title', 'seo_description', 'canonical_url')
        }),
    )

    def save_model(self, request, obj, form, change):
        try:
            super().save_model(request, obj, form, change)
        except Exception as e:
            messages.set_level(request, messages.ERROR)
            self.message_user(
                request,
                f"خطایی در هنگام ذخیره پست رخ داد: {e}",
                level=messages.ERROR
            )

@admin.register(Revision)
class RevisionAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    list_display = ('post', 'editor', 'created_at')
    list_filter = ('editor',)
    search_fields = ('post__title',)
