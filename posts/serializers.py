from django.apps import apps
from django.contrib.auth import get_user_model
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from jalali_date import datetime2jalali
from markdownify import markdownify as html_to_markdown
from rest_framework import serializers

from common.mixins import DynamicFieldsMixin
from medias.serializers import MediaDetailSerializer, PostMediaSerializer

from .models import AuthorProfile, Category, Post, Revision, Series, Tag

User = get_user_model()


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


class ContentNormalizationMixin:
    """
    EN: Mixin to normalize HTML content by converting it to Markdown and cleaning up whitespace.
    FA: Mixin برای نرمال‌سازی محتوای HTML با تبدیل آن به Markdown و پاکسازی فواصل خالی.
    """

    content_field_name = "content"

    def _normalize_content(self, value: str) -> str:
        """
        EN: Internal helper to perform HTML to Markdown conversion.
        FA: ابزار کمکی داخلی برای انجام تبدیل HTML به Markdown.
        """
        normalized = html_to_markdown(
            value,
            strip=["script", "style"],
            preserve_br=True,
            heading_style="ATX",
            escape_asterisks=False,
            escape_underscores=False,
            escape_md=False,
        )
        return normalized.replace("\xa0", " ").strip()

    def to_representation(self, instance):
        """
        EN: Overrides representation to include normalized content.
        FA: نمایش سریالایزر را برای شامل شدن محتوای نرمال‌سازی شده بازنویسی می‌کند.
        """
        data = super().to_representation(instance)
        content_value = data.get(self.content_field_name)
        if isinstance(content_value, str) and content_value.strip():
            data[self.content_field_name] = self._normalize_content(content_value)
        return data


class AuthorProfileSerializer(serializers.ModelSerializer):
    """
    EN: Serializer for AuthorProfile model.
    FA: سریالایزر برای مدل AuthorProfile.
    """

    class Meta:
        model = AuthorProfile
        fields = ("user", "display_name", "bio", "avatar")


class AuthorForPostSerializer(serializers.ModelSerializer):
    """
    EN: Minimal author serializer for inclusion in Post representation.
    FA: سریالایزر حداقلی نویسنده برای استفاده در نمایش پست.
    """

    avatar = MediaDetailSerializer(read_only=True)

    class Meta:
        model = AuthorProfile
        fields = ("display_name", "avatar")


class CategorySerializer(serializers.ModelSerializer):
    """
    EN: Serializer for Category model with support for parent categories.
    FA: سریالایزر برای مدل دسته‌بندی با پشتیبانی از دسته‌های والد.
    """

    class Meta:
        model = Category
        fields = ("id", "slug", "name", "parent")

    def to_representation(self, instance):
        """
        EN: Customizes parent category representation.
        FA: نمایش دسته‌بندی والد را سفارشی می‌کند.
        """
        representation = super().to_representation(instance)
        if instance.parent:
            representation["parent"] = {
                "id": instance.parent.id,
                "slug": instance.parent.slug,
                "name": instance.parent.name,
            }
        return representation


class TagSerializer(serializers.ModelSerializer):
    """
    EN: Serializer for Tag model.
    FA: سریالایزر برای مدل برچسب.
    """

    class Meta:
        model = Tag
        fields = ("id", "slug", "name")


class SeriesSerializer(serializers.ModelSerializer):
    """
    EN: Serializer for Series model.
    FA: سریالایزر برای مدل مجموعه.
    """

    class Meta:
        model = Series
        fields = "__all__"


class PostListSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    """
    EN: Optimized serializer for listing Posts with essential fields.
    FA: سریالایزر بهینه‌سازی شده برای لیست کردن پست‌ها با فیلدهای ضروری.
    """

    author = AuthorForPostSerializer(read_only=True)
    category = serializers.StringRelatedField()
    cover_media = MediaDetailSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)
    published_at = JalaliDateTimeField()

    class Meta:
        model = Post
        fields = (
            "id",
            "slug",
            "title",
            "excerpt",
            "reading_time_sec",
            "status",
            "is_hot",
            "published_at",
            "author",
            "category",
            "cover_media",
            "views_count",
            "likes_count",
            "comments_count",
            "tags",
        )


class PostDetailSerializer(ContentNormalizationMixin, PostListSerializer):
    """
    EN: Comprehensive serializer for detailed Post view, including content and attachments.
    FA: سریالایزر جامع برای نمای جزئیات پست، شامل محتوا و پیوست‌ها.
    """

    series = SeriesSerializer(read_only=True)
    og_image = MediaDetailSerializer(read_only=True)
    content = serializers.CharField()
    media_attachments = serializers.SerializerMethodField()

    class Meta(PostListSerializer.Meta):
        fields = PostListSerializer.Meta.fields + (
            "content",
            "canonical_url",
            "series",
            "seo_title",
            "seo_description",
            "og_image",
            "media_attachments",
        )

    @extend_schema_field(PostMediaSerializer(many=True))
    def get_media_attachments(self, obj):
        """
        EN: Retrieves media attachments related to the post.
        FA: پیوست‌های رسانه‌ای مرتبط با پست را واکشی می‌کند.
        """
        return PostMediaSerializer(obj.media_attachments.all(), many=True).data


class PostCreateUpdateSerializer(
    ContentNormalizationMixin, serializers.ModelSerializer
):
    """
    EN: Serializer for creating and updating Posts, handling complex fields like tags and scheduling.
    FA: سریالایزر برای ایجاد و به‌روزرسانی پست‌ها، با مدیریت فیلدهای پیچیده مانند برچسب‌ها و زمان‌بندی.
    """

    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        source="tags",
        required=False,
        write_only=True,
    )
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        required=False,
        write_only=True,
    )
    cover_media_id = serializers.PrimaryKeyRelatedField(
        queryset=apps.get_model("medias", "Media").objects.all(),
        source="cover_media",
        required=False,
        allow_null=True,
        write_only=True,
    )
    og_image_id = serializers.PrimaryKeyRelatedField(
        queryset=apps.get_model("medias", "Media").objects.all(),
        source="og_image",
        required=False,
        allow_null=True,
        write_only=True,
    )

    cover_media = MediaDetailSerializer(read_only=True)
    og_image = MediaDetailSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    published_at = JalaliDateTimeField()
    scheduled_at = JalaliDateTimeField()
    publish_at = serializers.DateTimeField(
        write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = Post
        fields = (
            "title",
            "excerpt",
            "content",
            "status",
            "visibility",
            "is_hot",
            "published_at",
            "scheduled_at",
            "category",
            "series",
            "cover_media",
            "seo_title",
            "seo_description",
            "og_image",
            "tags",
            "slug",
            "canonical_url",
            "views_count",
            "reading_time_sec",
            "tag_ids",
            "category_id",
            "cover_media_id",
            "og_image_id",
            "publish_at",
        )
        read_only_fields = ("views_count", "reading_time_sec")
        extra_kwargs = {"slug": {"required": False}}

    def _handle_publication_date(self, validated_data):
        """
        EN:
        Internal logic to handle 'published_at' and 'scheduled_at' based on the requested 'publish_at' date.
        It also manages status transitions between draft, scheduled, and published.

        FA:
        منطق داخلی برای مدیریت 'published_at' و 'scheduled_at' بر اساس تاریخ 'publish_at' درخواستی.
        همچنین تغییرات وضعیت بین پیش‌نویس، زمان‌بندی شده و منتشر شده را مدیریت می‌کند.
        """
        publish_at = validated_data.pop("publish_at", None)
        status = validated_data.get(
            "status", self.instance.status if self.instance else "draft"
        )

        if publish_at:
            if status == "published":
                if publish_at > timezone.now():
                    validated_data["status"] = "scheduled"
                    validated_data["scheduled_at"] = publish_at
                    validated_data["published_at"] = None
                else:
                    validated_data["status"] = "published"
                    validated_data["published_at"] = publish_at
                    validated_data["scheduled_at"] = None
            elif status == "draft":
                if publish_at > timezone.now():
                    validated_data["scheduled_at"] = publish_at
                else:
                    validated_data["scheduled_at"] = None
        elif status == "published" and (
            not self.instance or self.instance.status != "published"
        ):
            validated_data["published_at"] = timezone.now()

        return validated_data

    def create(self, validated_data):
        """
        EN: Handles post creation with publication date processing.
        FA: ایجاد پست را به همراه پردازش تاریخ انتشار مدیریت می‌کند.
        """
        validated_data = self._handle_publication_date(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        EN: Handles post update with publication date processing.
        FA: به‌روزرسانی پست را به همراه پردازش تاریخ انتشار مدیریت می‌کند.
        """
        validated_data = self._handle_publication_date(validated_data)
        return super().update(instance, validated_data)


class RevisionSerializer(serializers.ModelSerializer):
    """
    EN: Serializer for Post Revisions.
    FA: سریالایزر برای بازنگری‌های پست.
    """

    class Meta:
        model = Revision
        fields = "__all__"
