from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget

from .models import Post


class PostAdminForm(forms.ModelForm):
    """
    EN: Custom form for the Post admin, using CKEditor 5 for the content field.
    FA: فرم سفارشی برای ادمین پست، با استفاده از CKEditor 5 برای فیلد محتوا.
    """

    content = forms.CharField(widget=CKEditor5Widget(config_name="default"))

    class Meta:
        model = Post
        fields = "__all__"
