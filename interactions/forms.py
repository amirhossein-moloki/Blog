from django import forms

from .models import Comment


class CommentForm(forms.ModelForm):
    """
    EN: Standard form for creating or updating a Comment.
    FA: فرم استاندارد برای ایجاد یا به‌روزرسانی نظر.
    """

    class Meta:
        model = Comment
        fields = ("content",)
