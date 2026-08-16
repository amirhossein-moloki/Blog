from django.contrib.auth import get_user_model
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from jalali_date import datetime2jalali
from markdownify import markdownify as html_to_markdown
from rest_framework import serializers

from common.mixins import DynamicFieldsMixin, HybridMediaSerializerMixin
from medias.serializers import ArticleMediaSerializer, MediaDetailSerializer

from .models import (
    Article,
    AuthorProfile,
    Category,
    GalleryItem,
    Podcast,
    PodcastCategory,
    Revision,
    Series,
    Tag,
)

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


class HybridMediaField(serializers.Field):
    """
    EN: Custom field to accept either a Media ID (integer/string) or an uploaded file.
    FA: فیلد سفارشی برای پذیرش شناسه رسانه (عدد/رشته) یا فایل آپلود شده.
    """

    def to_internal_value(self, data):
        from django.apps import apps

        Media = apps.get_model("medias", "Media")

        if not data:
            return None

        if isinstance(data, Media):
            return data

        # Check if the data is a digit/integer (existing Media ID)
        if isinstance(data, (int, str)) and str(data).isdigit():
            try:
                return Media.objects.get(pk=int(data))
            except Media.DoesNotExist:
                raise serializers.ValidationError("Media with this ID does not exist.")

        # Check if the data is an uploaded file
        from django.core.files.uploadedfile import UploadedFile

        if isinstance(data, UploadedFile) or hasattr(data, "read"):
            request = self.context.get("request")
            if not request or not request.user or request.user.is_anonymous:
                raise serializers.ValidationError(
                    "Authentication is required to upload files."
                )

            from common.validators import validate_file

            try:
                validate_file(data)
            except Exception as e:
                raise serializers.ValidationError(str(e))

            from medias.services import create_media_from_file

            try:
                media_instance = create_media_from_file(data, request.user)
                # Track this processed media file to avoid reprocessing in inline content parsing
                serializer = self.parent
                if serializer:
                    if not hasattr(serializer, "_processed_files"):
                        serializer._processed_files = set()
                    serializer._processed_files.add(data.name)
                return media_instance
            except Exception as e:
                raise serializers.ValidationError(f"File upload failed: {str(e)}")

        raise serializers.ValidationError(
            "Invalid input. Must be an integer ID or a file."
        )

    def to_representation(self, value):
        if not value:
            return None
        from medias.serializers import MediaDetailSerializer

        return MediaDetailSerializer(value, context=self.context).data


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


class AuthorProfileSerializer(HybridMediaSerializerMixin, serializers.ModelSerializer):
    """
    EN: Serializer for AuthorProfile model.
    FA: سریالایزر برای مدل AuthorProfile.
    """

    avatar = HybridMediaField(required=False, allow_null=True)
    avatar_id = HybridMediaField(
        source="avatar", required=False, allow_null=True, write_only=True
    )

    hybrid_media_fields = (("avatar", "avatar_id"),)

    class Meta:
        model = AuthorProfile
        fields = ("user", "display_name", "bio", "avatar", "avatar_id")


class AuthorForArticleSerializer(serializers.ModelSerializer):
    """
    EN: Minimal author serializer for inclusion in Article representation.
    FA: سریالایزر حداقلی نویسنده برای استفاده در نمایش مقاله.
    """

    avatar = MediaDetailSerializer(read_only=True)

    class Meta:
        model = AuthorProfile
        fields = ("display_name", "avatar")


class CategorySerializer(HybridMediaSerializerMixin, serializers.ModelSerializer):
    """
    EN: Serializer for Category model with support for parent categories.
    FA: سریالایزر برای مدل دسته‌بندی با پشتیبانی از دسته‌های والد.
    """

    icon = HybridMediaField(required=False, allow_null=True)
    icon_id = HybridMediaField(
        source="icon", required=False, allow_null=True, write_only=True
    )

    hybrid_media_fields = (("icon", "icon_id"),)

    class Meta:
        model = Category
        fields = ("id", "slug", "name", "parent", "description", "order", "icon", "icon_id")

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


class ArticleListSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    """
    EN: Optimized serializer for listing Articles with essential fields.
    FA: سریالایزر بهینه‌سازی شده برای لیست کردن مقاله‌ها با فیلدهای ضروری.
    """

    author = AuthorForArticleSerializer(read_only=True)
    category = serializers.StringRelatedField()
    cover_image = MediaDetailSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)
    published_at = JalaliDateTimeField()

    slug = serializers.CharField(source="translation.slug", read_only=True)
    title = serializers.CharField(source="translation.title", read_only=True)
    excerpt = serializers.CharField(source="translation.excerpt", read_only=True)
    short_description = serializers.CharField(
        source="translation.short_description", read_only=True
    )
    reading_time_sec = serializers.IntegerField(
        source="translation.reading_time_sec", read_only=True
    )

    class Meta:
        model = Article
        fields = (
            "id",
            "slug",
            "title",
            "excerpt",
            "short_description",
            "reading_time_sec",
            "status",
            "is_hot",
            "published_at",
            "author",
            "category",
            "cover_image",
            "views_count",
            "likes_count",
            "comments_count",
            "tags",
        )


def migrate_and_normalize_block(block):
    """
    Normalizes on-the-fly and migrates old Visual configurations / structures
    to presentation-agnostic Headless CMS standards.
    """
    # 1. Ensure settings dict exists with universal presentation properties
    if "settings" not in block or not isinstance(block["settings"], dict):
        block["settings"] = {}

    settings_defaults = {
        "align": "left",
        "spacing": "md",
        "theme": "default",
        "visibility": "visible",
        "animation": "none",
        "width": "contained",
        "container": "default",
        "responsive": {},
        "custom_class": None,
    }
    for k, v in settings_defaults.items():
        if k not in block["settings"]:
            block["settings"][k] = v

    # 2. Migrate legacy visual properties from 'data' to 'settings'
    b_type = block.get("type")
    b_data = block.get("data", {})
    if isinstance(b_data, dict):
        if b_type == "divider" and "style" in b_data:
            block["settings"]["variant"] = b_data.pop("style")
        elif b_type == "button" and "style_preset" in b_data:
            block["settings"]["appearance"] = b_data.pop("style_preset")

    # 3. Ensure metadata/meta exists (accept both inputs, normalize to 'meta' output)
    meta_key = (
        "meta" if "meta" in block else ("metadata" if "metadata" in block else "meta")
    )
    meta_data = block.get(meta_key, {})
    if not isinstance(meta_data, dict):
        meta_data = {}

    meta_defaults = {
        "locked": False,
        "hidden": False,
        "created_by": None,
        "updated_by": None,
        "draft": False,
        "deleted": False,
        "internal_notes": "",
    }
    for k, v in meta_defaults.items():
        if k not in meta_data:
            meta_data[k] = v

    block["meta"] = meta_data
    if "metadata" in block:
        del block["metadata"]

    return block


class ArticleDetailSerializer(ContentNormalizationMixin, ArticleListSerializer):
    """
    EN: Comprehensive serializer for detailed Article view, including content and attachments.
    FA: سریالایزر جامع برای نمای جزئیات مقاله، شامل محتوا و پیوست‌ها.
    """

    series = SeriesSerializer(read_only=True)
    og_image = MediaDetailSerializer(read_only=True)
    content = serializers.CharField(source="translation.content", read_only=True)
    content_blocks = serializers.SerializerMethodField()
    blocks = serializers.SerializerMethodField()
    seo_title = serializers.CharField(source="translation.seo_title", read_only=True)
    seo_description = serializers.CharField(
        source="translation.seo_description", read_only=True
    )
    media_attachments = serializers.SerializerMethodField()
    related_articles = ArticleListSerializer(many=True, read_only=True)
    article_schema_version = serializers.SerializerMethodField()
    structured_data = serializers.SerializerMethodField()

    class Meta(ArticleListSerializer.Meta):
        fields = ArticleListSerializer.Meta.fields + (
            "content",
            "content_blocks",
            "blocks",
            "canonical_url",
            "series",
            "seo_title",
            "seo_description",
            "og_image",
            "media_attachments",
            "related_articles",
            "article_schema_version",
            "structured_data",
        )

    def get_article_schema_version(self, obj):
        return 2

    @extend_schema_field(ArticleMediaSerializer(many=True))
    def get_media_attachments(self, obj):
        """
        EN: Retrieves media attachments related to the article.
        FA: پیوست‌های رسانه‌ای مرتبط با مقاله را واکشی می‌کند.
        """
        # Pass the article object itself to the ArticleMediaSerializer context so it can compute references
        return ArticleMediaSerializer(
            obj.media_attachments.all(),
            many=True,
            context={"article": obj, "request": self.context.get("request")},
        ).data

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_blocks(self, obj):
        return self.get_content_blocks(obj)

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_content_blocks(self, obj):
        trans = obj.translation
        if not trans:
            return []
        blocks = trans.content_blocks or []
        if not blocks:
            return []

        import copy

        blocks = copy.deepcopy(blocks)

        # Collect all media_id and media_ids generically
        from posts.blocks import block_registry

        media_ids = set()
        for block in blocks:
            b_type = block.get("type")
            b_data = block.get("data", {})
            handler = block_registry.get_block(b_type)
            if handler:
                media_ids.update(handler.get_referenced_media_ids(b_data))

        # Query all Media records in a single query (batch expansion)
        from medias.models import Media
        from medias.serializers import MediaDetailSerializer

        media_map = {}
        if media_ids:
            medias = Media.objects.filter(id__in=media_ids)
            for media in medias:
                media_map[media.id] = MediaDetailSerializer(
                    media, context=self.context
                ).data

        # Embed Media into blocks generically & normalize / migrate on-the-fly
        normalized_blocks = []
        for block in blocks:
            b_type = block.get("type")
            b_data = block.get("data", {})
            handler = block_registry.get_block(b_type)
            if handler:
                handler.expand_media_references(b_data, media_map)
                handler.normalize_block_data(b_data)

                # Perform on-the-fly migration for settings, meta, and styles
                block = migrate_and_normalize_block(block)
                normalized_blocks.append(block)

        return normalized_blocks

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_structured_data(self, obj):
        processed_blocks = self.get_content_blocks(obj)
        from posts.blocks import block_registry

        structured_data = []
        for block in processed_blocks:
            b_type = block.get("type")
            b_data = block.get("data", {})
            handler = block_registry.get_block(b_type)
            if handler:
                seo_meta = handler.get_seo_metadata(b_data)
                if seo_meta:
                    if isinstance(seo_meta, list):
                        structured_data.extend(seo_meta)
                    else:
                        structured_data.append(seo_meta)
        return structured_data


class ArticleCreateUpdateSerializer(
    ContentNormalizationMixin, HybridMediaSerializerMixin, serializers.ModelSerializer
):
    """
    EN: Serializer for creating and updating Articles, handling complex fields like tags and scheduling.
    FA: سریالایزر برای ایجاد و به‌روزرسانی مقاله‌ها، با مدیریت فیلدهای پیچیده مانند برچسب‌ها و زمان‌بندی.
    """

    language_code = serializers.CharField(write_only=True, default="en")
    title = serializers.CharField(write_only=True)
    slug = serializers.SlugField(write_only=True, required=False)
    excerpt = serializers.CharField(write_only=True)
    short_description = serializers.CharField(
        write_only=True, required=False, allow_blank=True, allow_null=True
    )
    content = serializers.CharField(
        write_only=True, required=False, allow_blank=True, allow_null=True
    )
    content_blocks = serializers.JSONField(write_only=True, required=False)
    seo_title = serializers.CharField(write_only=True, required=False, allow_blank=True)
    seo_description = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )

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
    cover_image = HybridMediaField(required=False, allow_null=True)
    cover_image_id = HybridMediaField(
        source="cover_image",
        required=False,
        allow_null=True,
        write_only=True,
    )
    og_image = HybridMediaField(required=False, allow_null=True)
    og_image_id = HybridMediaField(
        source="og_image",
        required=False,
        allow_null=True,
        write_only=True,
    )

    hybrid_media_fields = (
        ("cover_image", "cover_image_id"),
        ("og_image", "og_image_id"),
    )
    related_article_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Article.objects.all(),
        source="related_articles",
        required=False,
        write_only=True,
    )

    cover_image = MediaDetailSerializer(read_only=True)
    og_image = MediaDetailSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    published_at = JalaliDateTimeField()
    scheduled_at = JalaliDateTimeField()
    publish_at = serializers.DateTimeField(
        write_only=True, required=False, allow_null=True
    )
    related_articles = ArticleListSerializer(many=True, read_only=True)

    class Meta:
        model = Article
        fields = (
            "id",
            "language_code",
            "title",
            "excerpt",
            "short_description",
            "content",
            "content_blocks",
            "status",
            "visibility",
            "is_hot",
            "published_at",
            "scheduled_at",
            "category",
            "series",
            "cover_image",
            "seo_title",
            "seo_description",
            "og_image",
            "tags",
            "slug",
            "canonical_url",
            "views_count",
            "tag_ids",
            "category_id",
            "cover_image_id",
            "og_image_id",
            "related_article_ids",
            "related_articles",
            "publish_at",
        )
        read_only_fields = ("views_count",)
        extra_kwargs = {"slug": {"required": False}}

    def validate_content_blocks(self, value):
        if value is None:
            return []

        request = self.context.get("request")
        if request and request.FILES and request.user and not request.user.is_anonymous:
            from medias.services import process_inline_blocks_media

            value = process_inline_blocks_media(value, request.FILES, request.user)

        from django.core.exceptions import ValidationError as DjangoValidationError

        from posts.services import validate_and_sanitize_blocks

        language_code = self.initial_data.get("language_code", "en")
        try:
            return validate_and_sanitize_blocks(value, language_code=language_code)
        except DjangoValidationError as e:
            if hasattr(e, "message_dict") and e.message_dict:
                raise serializers.ValidationError(e.message_dict)
            raise serializers.ValidationError(e.message)

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

    def _process_inline_files(self, content):
        if not content:
            return content

        request = self.context.get("request")
        if not request or not request.user or request.user.is_anonymous:
            return content

        import os

        from bs4 import BeautifulSoup

        from common.validators import validate_file
        from medias.services import create_media_from_file

        soup = BeautifulSoup(content, "html.parser")
        img_tags = soup.find_all("img")
        if not img_tags or not request.FILES:
            return content

        for img_tag in img_tags:
            src = img_tag.get("src", "")
            if not src:
                continue
            src_filename = os.path.basename(src)

            # Find a matching file in request.FILES by its filename
            for name, file_obj in request.FILES.items():
                processed_names = getattr(self, "_processed_files", set())
                if file_obj.name in processed_names:
                    continue

                if file_obj.name == src_filename:
                    # Validate and create Media
                    try:
                        validate_file(file_obj)
                    except Exception as e:
                        raise serializers.ValidationError(
                            f"Inline file validation failed: {str(e)}"
                        )

                    media_instance = create_media_from_file(file_obj, request.user)
                    img_tag["src"] = media_instance.url

                    if not hasattr(self, "_processed_files"):
                        self._processed_files = set()
                    self._processed_files.add(file_obj.name)
                    break

        return str(soup)

    def create(self, validated_data):
        """
        EN: Handles article and translation creation with publication date processing.
        FA: ایجاد مقاله و ترجمه را به همراه پردازش تاریخ انتشار مدیریت می‌کند.
        """
        from django.db import transaction

        from .models import ArticleTranslation

        translation_data = {
            "language_code": validated_data.pop("language_code", "en"),
            "title": validated_data.pop("title"),
            "slug": validated_data.pop("slug", ""),
            "excerpt": validated_data.pop("excerpt"),
            "short_description": validated_data.pop("short_description", ""),
            "content": validated_data.pop("content", ""),
            "content_blocks": validated_data.pop("content_blocks", []),
            "seo_title": validated_data.pop("seo_title", ""),
            "seo_description": validated_data.pop("seo_description", ""),
        }
        if "content" in translation_data and translation_data["content"]:
            translation_data["content"] = self._process_inline_files(
                translation_data["content"]
            )

        if not translation_data["slug"]:
            from django.utils.text import slugify

            translation_data["slug"] = slugify(translation_data["title"])

        validated_data = self._handle_publication_date(validated_data)

        with transaction.atomic():
            article = super().create(validated_data)
            ArticleTranslation.objects.create(article=article, **translation_data)

        return article

    def update(self, instance, validated_data):
        """
        EN: Handles article and translation update with publication date processing.
        FA: به‌روزرسانی مقاله و ترجمه را به همراه پردازش تاریخ انتشار مدیریت می‌کند.
        """
        from django.db import transaction

        from .models import ArticleTranslation

        language_code = validated_data.pop("language_code", "en")
        translation_fields = [
            "title",
            "slug",
            "excerpt",
            "short_description",
            "content",
            "content_blocks",
            "seo_title",
            "seo_description",
        ]
        translation_data = {}
        for field in translation_fields:
            if field in validated_data:
                translation_data[field] = validated_data.pop(field)

        if "content" in translation_data and translation_data["content"]:
            translation_data["content"] = self._process_inline_files(
                translation_data["content"]
            )

        validated_data = self._handle_publication_date(validated_data)

        with transaction.atomic():
            article = super().update(instance, validated_data)
            if translation_data:
                ArticleTranslation.objects.update_or_create(
                    article=article,
                    language_code=language_code,
                    defaults=translation_data,
                )

        return article


class RevisionSerializer(serializers.ModelSerializer):
    """
    EN: Serializer for Article Revisions.
    FA: سریالایزر برای بازنگری‌های مقاله.
    """

    class Meta:
        model = Revision
        fields = "__all__"


class PodcastCategorySerializer(HybridMediaSerializerMixin, serializers.ModelSerializer):
    """
    EN: Serializer for PodcastCategory model.
    FA: سریالایزر برای مدل دسته‌بندی پادکست.
    """

    icon = HybridMediaField(required=False, allow_null=True)
    icon_id = HybridMediaField(
        source="icon", required=False, allow_null=True, write_only=True
    )

    hybrid_media_fields = (("icon", "icon_id"),)

    class Meta:
        model = PodcastCategory
        fields = ("id", "title", "slug", "icon", "icon_id", "is_active")


class PodcastSerializer(
    ContentNormalizationMixin, HybridMediaSerializerMixin, serializers.ModelSerializer
):
    """
    EN: Serializer for Podcast model.
    FA: سریالایزر برای مدل پادکست.
    """

    content_field_name = "description"
    category_detail = PodcastCategorySerializer(source="category", read_only=True)
    published_date_jalali = JalaliDateTimeField(source="published_date", read_only=True)

    cover_image = HybridMediaField(required=False, allow_null=True)
    cover_image_id = HybridMediaField(
        source="cover_image", required=False, allow_null=True, write_only=True
    )
    audio_file = HybridMediaField(required=False, allow_null=True)
    audio_file_id = HybridMediaField(
        source="audio_file", required=False, allow_null=True, write_only=True
    )
    video_file = HybridMediaField(required=False, allow_null=True)
    video_file_id = HybridMediaField(
        source="video_file", required=False, allow_null=True, write_only=True
    )

    hybrid_media_fields = (
        ("cover_image", "cover_image_id"),
        ("audio_file", "audio_file_id"),
        ("video_file", "video_file_id"),
    )

    class Meta:
        model = Podcast
        fields = (
            "id",
            "title",
            "slug",
            "category",
            "category_detail",
            "episode_number",
            "cover_image",
            "cover_image_id",
            "audio_file",
            "audio_file_id",
            "media_type",
            "video_file",
            "video_file_id",
            "video_url",
            "description",
            "duration",
            "published_date",
            "published_date_jalali",
            "view_count",
            "related_podcasts",
            "is_active",
        )
        read_only_fields = ("view_count",)


class GalleryItemSerializer(HybridMediaSerializerMixin, serializers.ModelSerializer):
    """
    EN: Serializer for GalleryItem model.
    FA: سریالایزر برای مدل گالری تصاویر.
    """

    image = HybridMediaField(required=False, allow_null=True)
    image_id = HybridMediaField(
        source="image", required=False, allow_null=True, write_only=True
    )

    hybrid_media_fields = (("image", "image_id"),)

    class Meta:
        model = GalleryItem
        fields = ("id", "image", "image_id", "caption", "order", "link", "is_active")
