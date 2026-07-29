from django.contrib.auth import get_user_model
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from core.base_models import BaseModel

User = get_user_model()


class Media(BaseModel):
    """
    EN:
    Represents a media file (image, video, etc.) stored in the system.
    Stores metadata like dimensions, MIME type, and size.

    FA:
    نشان‌دهنده یک فایل رسانه‌ای (تصویر، ویدیو و غیره) ذخیره شده در سیستم.
    متادیتاهایی مانند ابعاد، نوع MIME و حجم را ذخیره می‌کند.
    """

    STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("Processing", "Processing"),
        ("Ready", "Ready"),
        ("Rejected", "Rejected"),
        ("Quarantined", "Quarantined"),
    )

    class Meta:
        ordering = ["-created_at"]

    storage_key = models.CharField(max_length=255)
    url = models.URLField()
    type = models.CharField(
        max_length=50
    )  # EN: image/video/audio/file | FA: تصویر/ویدیو/صوتی/فایل
    mime = models.CharField(max_length=100)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    duration = models.PositiveIntegerField(
        null=True, blank=True
    )  # EN: in seconds | FA: به ثانیه
    size_bytes = models.PositiveIntegerField(default=0)
    alt_text = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    # Added enterprise features
    is_deleted = models.BooleanField(default=False)
    content_hash = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    checksum_algorithm = models.CharField(max_length=10, default="SHA256")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Ready",
    )

    def __str__(self):
        """
        EN: Returns the title or storage key as the string representation.
        FA: عنوان یا کلید ذخیره‌سازی را به عنوان نمایش رشته‌ای بازمی‌گرداند.
        """
        return self.title or self.storage_key

    def get_download_url(self):
        """
        EN: Returns the internal URL to download the media file.
        FA: آدرس داخلی برای دانلود فایل رسانه را بازمی‌گرداند.
        """
        if self.pk:
            return reverse("medias:download_media", kwargs={"media_id": self.pk})
        return ""


class MediaVariant(BaseModel):
    """
    EN:
    Stores processed variants of a parent Media object (e.g., thumbnail, small, medium, large).
    Supports multi-format delivery (JPEG, PNG, WebP, AVIF).

    FA:
    نسخه‌های پردازش شده از یک شیء رسانه والد را ذخیره می‌کند (مانند تامبنیل، کوچک، متوسط، بزرگ).
    از فرمت‌های چندگانه تحویل پشتیبانی می‌کند.
    """

    media = models.ForeignKey(Media, on_delete=models.CASCADE, related_name="variants")
    variant_name = models.CharField(max_length=50)  # e.g., 'original', 'large', 'medium', 'small', 'thumbnail'
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    format = models.CharField(max_length=20)  # e.g., 'JPEG', 'PNG', 'WebP', 'AVIF'
    storage_key = models.CharField(max_length=255)
    url = models.URLField()
    size_bytes = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["variant_name"]

    def __str__(self):
        return f"{self.variant_name} variant of Media {self.media_id}"


class ArticleMedia(BaseModel):
    """
    EN:
    Relationship model linking Media to Articles.
    Specifies how a media file is used within an article (e.g., cover, in-content).

    FA:
    مدل رابط که رسانه را به مقاله‌ها پیوند می‌دهد.
    مشخص می‌کند که یک فایل رسانه چگونه در یک مقاله استفاده شده است (مثلاً تصویر کاور یا داخل محتوا).
    """

    article = models.ForeignKey(
        "posts.Article", on_delete=models.CASCADE, related_name="media_attachments"
    )
    media = models.ForeignKey(
        Media, on_delete=models.CASCADE, related_name="article_attachments"
    )
    attachment_type = models.CharField(
        max_length=50, default="in-content"
    )  # EN: e.g., 'in-content', 'cover', 'og-image'

    class Meta:
        unique_together = ("article", "media", "attachment_type")
        verbose_name = _("Article Media")
        verbose_name_plural = _("Article Media")

    def __str__(self):
        """
        EN: Returns a description of the attachment.
        FA: توضیحی در مورد پیوست رسانه بازمی‌گرداند.
        """
        return f"{self.media.title} attached to article {self.article_id} as {self.attachment_type}"
