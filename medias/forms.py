from django import forms
from django.contrib.admin.widgets import AdminFileWidget
from django.utils.html import format_html

from .models import Media


class ImagePreviewWidget(AdminFileWidget):
    """
    EN: Custom Admin widget to display an image preview for file fields in the Django admin.
    FA: ویجت سفارشی ادمین برای نمایش پیش‌نمایش تصویر برای فیلدهای فایل در پنل ادمین جنگو.
    """

    def render(self, name, value, attrs=None, renderer=None):
        """
        EN: Renders the file input with an image thumbnail if available.
        FA: ورودی فایل را همراه با یک تصویر بندانگشتی (در صورت موجود بودن) نمایش می‌دهد.
        """
        output = []
        if value and getattr(value, "url", None):
            image_url = value.url
            file_name = str(value)
            output.append(
                f'<a href="{image_url}" target="_blank">'
                f'<img src="{image_url}" alt="{file_name}" width="150" height="150" '
                f'style="object-fit: cover;"/></a>'
            )
        output.append(super().render(name, value, attrs, renderer))
        return format_html("".join(output))


class MediaAdminForm(forms.ModelForm):
    """
    EN: Form for managing Media objects in the Django admin interface.
    FA: فرم برای مدیریت اشیاء رسانه در رابط کاربری ادمین جنگو.
    """

    file = forms.FileField(required=False)

    class Meta:
        model = Media
        fields = (
            "file",
            "alt_text",
            "title",
            "storage_key",
            "url",
            "type",
            "mime",
            "size_bytes",
            "uploaded_by",
        )
