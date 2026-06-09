from django.contrib import admin
from jalali_date.admin import ModelAdminJalaliMixin
from .models import Comment, Reaction

@admin.register(Comment)
class CommentAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    list_display = ('user', 'post', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'content')

@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'reaction', 'content_object', 'created_at')
    list_filter = ('reaction',)
