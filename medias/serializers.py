from jalali_date import datetime2jalali
from rest_framework import serializers

from common.validators import validate_file

from .models import ArticleMedia, Media
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
    EN: Detailed serializer for the Media model, including Jalali creation date, metadata, and variants.
    FA: سریالایزر جزئیات برای مدل رسانه، شامل تاریخ ایجاد جلالی، متادیتا و نسخه‌های مختلف فایل.
    """

    created_at = JalaliDateTimeField()
    updated_at = JalaliDateTimeField()

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
            "updated_at",
            "status",
            "is_deleted",
            "content_hash",
            "checksum_algorithm",
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # Structure nested metadata
        data["metadata"] = {
            "width": instance.width,
            "height": instance.height,
            "mime": instance.mime,
            "size": instance.size_bytes,
        }

        # Structure nested variants
        variants_dict = {}
        for variant in instance.variants.all():
            variants_dict[variant.variant_name] = variant.url
        data["variants"] = variants_dict

        # Expanded Headless CMS Media payload attributes
        data["dominant_color"] = "#ffffff"
        data["blur_hash"] = "L6PZf9e.D%f_00%~9FpI_3WBMybH"
        data["placeholder"] = None

        # Detect animated status (GIF, APNG, WEBP, or video files)
        is_animated = False
        mime_lower = (instance.mime or "").lower()
        if "gif" in mime_lower or "video" in mime_lower or "mp4" in mime_lower:
            is_animated = True
        data["is_animated"] = is_animated

        data["checksum"] = instance.content_hash
        data["storage_provider"] = "local"

        return data


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


class ArticleMediaSerializer(serializers.ModelSerializer):
    """
    EN: Serializer for the relationship between Articles and Media.
    FA: سریالایزر برای رابطه بین مقاله‌ها و رسانه‌ها.
    """

    media = MediaDetailSerializer(read_only=True)

    class Meta:
        model = ArticleMedia
        fields = ("media", "attachment_type")

    def to_representation(self, instance):
        data = super().to_representation(instance)

        usage_count = 0
        referenced_by = []
        lock_status = False

        article = self.context.get("article")
        if article and article.translation:
            blocks = article.translation.content_blocks or []
            media_id = instance.media.id if instance.media else None

            from posts.blocks import block_registry

            for block in blocks:
                b_type = block.get("type")
                b_data = block.get("data", {})
                b_id = block.get("id")
                handler = block_registry.get_block(b_type)
                if handler:
                    ref_ids = handler.get_referenced_media_ids(b_data)
                    if media_id in ref_ids:
                        usage_count += 1
                        if b_id:
                            referenced_by.append(b_id)

            # Attached as cover, og-image, or has content-block references
            if usage_count > 0 or instance.attachment_type in ["cover", "og-image"]:
                lock_status = True

        data["usage_count"] = usage_count
        data["referenced_by"] = referenced_by
        data["lock_status"] = lock_status
        return data
