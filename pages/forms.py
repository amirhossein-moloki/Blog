from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget

from .models import Page


class PageAdminForm(forms.ModelForm):
    """
    EN: Custom form for the Page admin, using CKEditor 5 for the content field.
    FA: فرم سفارشی برای ادمین صفحه، با استفاده از CKEditor 5 برای فیلد محتوا.
    """

    content = forms.CharField(widget=CKEditor5Widget(config_name="default"))

    class Meta:
        model = Page
        fields = "__all__"
