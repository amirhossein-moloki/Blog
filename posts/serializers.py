from django.apps import apps
from django.contrib.auth import get_user_model
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from jalali_date import datetime2jalali
from markdownify import markdownify as html_to_markdown
from rest_framework import serializers

from common.mixins import DynamicFieldsMixin
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


class AuthorForArticleSerializer(serializers.ModelSerializer):
    """
    EN: Minimal author serializer for inclusion in Article representation.
    FA: سریالایزر حداقلی نویسنده برای استفاده در نمایش مقاله.
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
        fields = ("id", "slug", "name", "parent", "icon")

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


class ArticleDetailSerializer(ContentNormalizationMixin, ArticleListSerializer):
    """
    EN: Comprehensive serializer for detailed Article view, including content and attachments.
    FA: سریالایزر جامع برای نمای جزئیات مقاله، شامل محتوا و پیوست‌ها.
    """

    series = SeriesSerializer(read_only=True)
    og_image = MediaDetailSerializer(read_only=True)
    content = serializers.CharField(source="translation.content", read_only=True)
    seo_title = serializers.CharField(source="translation.seo_title", read_only=True)
    seo_description = serializers.CharField(
        source="translation.seo_description", read_only=True
    )
    media_attachments = serializers.SerializerMethodField()
    related_articles = ArticleListSerializer(many=True, read_only=True)

    class Meta(ArticleListSerializer.Meta):
        fields = ArticleListSerializer.Meta.fields + (
            "content",
            "canonical_url",
            "series",
            "seo_title",
            "seo_description",
            "og_image",
            "media_attachments",
            "related_articles",
        )

    @extend_schema_field(ArticleMediaSerializer(many=True))
    def get_media_attachments(self, obj):
        """
        EN: Retrieves media attachments related to the article.
        FA: پیوست‌های رسانه‌ای مرتبط با مقاله را واکشی می‌کند.
        """
        return ArticleMediaSerializer(obj.media_attachments.all(), many=True).data


class ArticleCreateUpdateSerializer(
    ContentNormalizationMixin, serializers.ModelSerializer
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
    content = serializers.CharField(write_only=True)
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
    cover_image_id = serializers.PrimaryKeyRelatedField(
        queryset=apps.get_model("medias", "Media").objects.all(),
        source="cover_image",
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

    def to_internal_value(self, data):
        import json
        import re
        from medias.services import create_media_from_file

        request = self.context.get("request")

        # Check if we are using Workflow A (New) or Workflow B (Legacy)
        if "article" in data:
            article_data = data["article"]
            if isinstance(article_data, str):
                try:
                    article_data = json.loads(article_data)
                except json.JSONDecodeError as e:
                    raise serializers.ValidationError({"article": f"Invalid JSON format: {str(e)}"})
            if not isinstance(article_data, dict):
                raise serializers.ValidationError({"article": "Article data must be a JSON object."})
        else:
            # Workflow B (Legacy) or direct field dictionary
            if hasattr(data, "copy"):
                article_data = data.copy()
            else:
                article_data = dict(data)

        # Process uploaded files if request is available
        pending_attachments = []
        if request:
            # 1. Process cover_image
            if "cover_image" in request.FILES:
                cover_media = create_media_from_file(request.FILES["cover_image"], request.user)
                if not hasattr(request, "_uploaded_media"):
                    request._uploaded_media = []
                request._uploaded_media.append(cover_media.storage_key)
                article_data["cover_image_id"] = cover_media.id
                article_data.pop("cover_image", None)

            # 2. Process og_image
            if "og_image" in request.FILES:
                og_media = create_media_from_file(request.FILES["og_image"], request.user)
                if not hasattr(request, "_uploaded_media"):
                    request._uploaded_media = []
                request._uploaded_media.append(og_media.storage_key)
                article_data["og_image_id"] = og_media.id
                article_data.pop("og_image", None)

            # 3. Process files[<upload_id>]
            upload_id_to_media = {}
            for key in request.FILES:
                match = re.match(r'^files\[(.*)\]$', key)
                if match:
                    upload_id = match.group(1)
                    uploaded_file = request.FILES[key]
                    media_obj = create_media_from_file(uploaded_file, request.user)
                    if not hasattr(request, "_uploaded_media"):
                        request._uploaded_media = []
                    request._uploaded_media.append(media_obj.storage_key)
                    upload_id_to_media[upload_id] = media_obj

            # 4. Rewrite temporary image references in content
            content = article_data.get("content", "")
            replaced_upload_ids = set()
            if content and isinstance(content, str):
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')
                modified = False
                for img in soup.find_all('img'):
                    if img.has_attr('data-upload-id'):
                        upload_id = img['data-upload-id']
                        if upload_id in upload_id_to_media:
                            media_obj = upload_id_to_media[upload_id]
                            img['src'] = media_obj.url
                            del img['data-upload-id']
                            replaced_upload_ids.add(upload_id)
                            modified = True
                if modified:
                    article_data["content"] = str(soup)

            # 5. Handle any files not embedded in content as pending attachments
            for upload_id, media_obj in upload_id_to_media.items():
                if upload_id not in replaced_upload_ids:
                    prefix_match = re.match(r'^([a-zA-Z_-]+)', upload_id)
                    attachment_type = prefix_match.group(1).lower() if prefix_match else "attachment"
                    if attachment_type in ["img", "image"]:
                        attachment_type = "image"
                    pending_attachments.append((media_obj, attachment_type))

        validated_data = super().to_internal_value(article_data)
        validated_data["_pending_attachments"] = pending_attachments
        return validated_data

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
        EN: Handles article and translation creation with publication date processing.
        FA: ایجاد مقاله و ترجمه را به همراه پردازش تاریخ انتشار مدیریت می‌کند.
        """
        from django.db import transaction

        from .models import ArticleTranslation

        pending_attachments = validated_data.pop("_pending_attachments", [])

        translation_data = {
            "language_code": validated_data.pop("language_code", "en"),
            "title": validated_data.pop("title"),
            "slug": validated_data.pop("slug", ""),
            "excerpt": validated_data.pop("excerpt"),
            "short_description": validated_data.pop("short_description", ""),
            "content": validated_data.pop("content"),
            "seo_title": validated_data.pop("seo_title", ""),
            "seo_description": validated_data.pop("seo_description", ""),
        }
        if not translation_data["slug"]:
            from django.utils.text import slugify

            translation_data["slug"] = slugify(translation_data["title"])

        validated_data = self._handle_publication_date(validated_data)

        with transaction.atomic():
            article = super().create(validated_data)
            ArticleTranslation.objects.create(article=article, **translation_data)

            # Create ArticleMedia relations for pending non-content attachments
            from medias.models import ArticleMedia
            for media_obj, attachment_type in pending_attachments:
                ArticleMedia.objects.update_or_create(
                    article=article,
                    media=media_obj,
                    defaults={"attachment_type": attachment_type}
                )

        return article

    def update(self, instance, validated_data):
        """
        EN: Handles article and translation update with publication date processing.
        FA: به‌روزرسانی مقاله و ترجمه را به همراه پردازش تاریخ انتشار مدیریت می‌کند.
        """
        from django.db import transaction

        from .models import ArticleTranslation

        pending_attachments = validated_data.pop("_pending_attachments", [])

        language_code = validated_data.pop("language_code", "en")
        translation_fields = [
            "title",
            "slug",
            "excerpt",
            "short_description",
            "content",
            "seo_title",
            "seo_description",
        ]
        translation_data = {}
        for field in translation_fields:
            if field in validated_data:
                translation_data[field] = validated_data.pop(field)

        validated_data = self._handle_publication_date(validated_data)

        with transaction.atomic():
            article = super().update(instance, validated_data)
            if translation_data:
                ArticleTranslation.objects.update_or_create(
                    article=article,
                    language_code=language_code,
                    defaults=translation_data,
                )

            # Create ArticleMedia relations for pending non-content attachments
            from medias.models import ArticleMedia
            for media_obj, attachment_type in pending_attachments:
                ArticleMedia.objects.update_or_create(
                    article=article,
                    media=media_obj,
                    defaults={"attachment_type": attachment_type}
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


class PodcastCategorySerializer(serializers.ModelSerializer):
    """
    EN: Serializer for PodcastCategory model.
    FA: سریالایزر برای مدل دسته‌بندی پادکست.
    """

    class Meta:
        model = PodcastCategory
        fields = ("id", "title", "slug", "icon", "is_active")


class PodcastSerializer(ContentNormalizationMixin, serializers.ModelSerializer):
    """
    EN: Serializer for Podcast model.
    FA: سریالایزر برای مدل پادکست.
    """

    content_field_name = "description"
    category_detail = PodcastCategorySerializer(source="category", read_only=True)
    published_date_jalali = JalaliDateTimeField(source="published_date", read_only=True)

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
            "audio_file",
            "media_type",
            "video_file",
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


class GalleryItemSerializer(serializers.ModelSerializer):
    """
    EN: Serializer for GalleryItem model.
    FA: سریالایزر برای مدل گالری تصاویر.
    """

    class Meta:
        model = GalleryItem
        fields = ("id", "image", "caption", "order", "link", "is_active")
