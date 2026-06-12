from jalali_date import datetime2jalali
from rest_framework import serializers

from common.validators import validate_file

from .models import Media, PostMedia
from .services import create_media_from_file


class JalaliDateTimeField(serializers.ReadOnlyField):
    """
    EN: Custom field to represent datetime in Jalali (Persian) format.
    FA: فیلد سفارشی برای نمایش تاریخ و زمان در قالب جلالی (شمسی).
    """

    def to_representation(self, value):
        """
        EN: Converts the datetime object to a Jalali date string.
        FA: تبدیل شیء datetime به رشته تاریخ جلالی.
        """
        if value:
            return datetime2jalali(value).strftime("%Y/%m/%d %H:%M:%S")
        return None


class MediaDetailSerializer(serializers.ModelSerializer):
    """
    EN: Detailed serializer for the Media model, including Jalali creation date.
    FA: سریالایزر جزئیات برای مدل رسانه، شامل تاریخ ایجاد جلالی.
    """

    created_at = JalaliDateTimeField()

    class Meta:
        model = Media
        fields = (
            "id",
            "storage_key",
            "url",
            "type",
            "mime",
            "width",
            "height",
            "duration",
            "size_bytes",
            "alt_text",
            "title",
            "uploaded_by",
            "created_at",
        )


class MediaCreateSerializer(serializers.ModelSerializer):
    """
    EN: Serializer for uploading new media files. Validates file size and type.
    FA: سریالایزر برای آپلود فایل‌های رسانه‌ای جدید. حجم و نوع فایل را اعتبارسنجی می‌کند.
    """

    file = serializers.FileField(write_only=True, validators=[validate_file])

    class Meta:
        model = Media
        fields = ("file", "alt_text", "title")

    def create(self, validated_data):
        """
        EN: Uses the media service to handle file upload and metadata extraction.
        FA: از سرویس رسانه برای مدیریت آپلود فایل و استخراج متادیتا استفاده می‌کند.
        """
        file = validated_data.pop("file")
        uploaded_by = self.context["request"].user
        return create_media_from_file(file, uploaded_by, **validated_data)


class PostMediaSerializer(serializers.ModelSerializer):
    """
    EN: Serializer for the relationship between Posts and Media.
    FA: سریالایزر برای رابطه بین پست‌ها و رسانه‌ها.
    """

    media = MediaDetailSerializer(read_only=True)

    class Meta:
        model = PostMedia
        fields = ("media", "attachment_type")
