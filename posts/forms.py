from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget

from .models import Article


class ArticleAdminForm(forms.ModelForm):
    """
    EN: Custom form for the Article admin, using CKEditor 5 for the content field.
    FA: فرم سفارشی برای ادمین مقاله، با استفاده از CKEditor 5 برای فیلد محتوا.
    """

    content = forms.CharField(widget=CKEditor5Widget(config_name="default"))

    class Meta:
        model = Article
        fields = "__all__"
