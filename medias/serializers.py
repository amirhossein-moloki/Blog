from jalali_date import datetime2jalali
from rest_framework import serializers

from common.validators import validate_file

from .models import Media, PostMedia
from .services import create_media_from_file


class JalaliDateTimeField(serializers.ReadOnlyField):
    def to_representation(self, value):
        if value:
            return datetime2jalali(value).strftime("%Y/%m/%d %H:%M:%S")
        return None


class MediaDetailSerializer(serializers.ModelSerializer):
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
    file = serializers.FileField(write_only=True, validators=[validate_file])

    class Meta:
        model = Media
        fields = ("file", "alt_text", "title")

    def create(self, validated_data):
        file = validated_data.pop("file")
        uploaded_by = self.context["request"].user
        return create_media_from_file(file, uploaded_by, **validated_data)


class PostMediaSerializer(serializers.ModelSerializer):
    media = MediaDetailSerializer(read_only=True)

    class Meta:
        model = PostMedia
        fields = ("media", "attachment_type")
