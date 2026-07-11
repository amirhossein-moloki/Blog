import re

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.urls import reverse
from django_ckeditor_5.fields import CKEditor5Field

from core.base_models import BaseModel

User = get_user_model()


class AuthorProfile(BaseModel):
    """
    EN:
    Extended profile for authors, linked to the User model.
    Stores professional information like bio and display name.

    FA:
    پروفایل گسترش یافته برای نویسندگان، متصل به مدل کاربر.
    اطلاعات حرفه‌ای مانند بیوگرافی و نام نمایشی را ذخیره می‌کند.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    display_name = models.CharField(max_length=255)
    bio = models.TextField(blank=True)
    avatar = models.ForeignKey(
        "medias.Media", on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        """
        EN: Returns the display name of the author.
        FA: نام نمایشی نویسنده را بازمی‌گرداند.
        """
        return self.display_name


class Category(BaseModel):
    """
    EN:
    Represents a category for posts, supporting a hierarchical structure.
    Categories can have parent and child categories.

    FA:
    نشان‌دهنده دسته‌بندی برای پست‌ها، با پشتیبانی از ساختار سلسله‌مراتبی.
    دسته‌بندی‌ها می‌توانند دسته‌های والد و فرزند داشته باشند.
    """

    slug = models.SlugField(unique=True, allow_unicode=True)
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    icon = models.FileField(upload_to="categories/icons/", null=True, blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        """
        EN: Returns the name of the category.
        FA: نام دسته‌بندی را بازمی‌گرداند.
        """
        return self.name


class Tag(BaseModel):
    """
    EN: Represents a tag used to label posts for better searchability.
    FA: نشان‌دهنده برچسبی که برای برچسب‌گذاری پست‌ها جهت جستجوی بهتر استفاده می‌شود.
    """

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):
        """
        EN: Returns the name of the tag.
        FA: نام برچسب را بازمی‌گرداند.
        """
        return self.name


class Series(BaseModel):
    """
    EN: Represents a series of posts that belong together.
    FA: نشان‌دهنده مجموعه‌ای از پست‌ها که به هم تعلق دارند.
    """

    ORDER_STRATEGY_CHOICES = (
        ("manual", "Manual"),
        ("by_date", "By Date"),
    )
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order_strategy = models.CharField(
        max_length=10, choices=ORDER_STRATEGY_CHOICES, default="manual"
    )

    class Meta:
        verbose_name_plural = "Series"

    def __str__(self):
        """
        EN: Returns the title of the series.
        FA: عنوان مجموعه را بازمی‌گرداند.
        """
        return self.title

    def get_absolute_url(self):
        """
        EN: Returns the absolute URL for the series detail view.
        FA: آدرس مطلق برای نمای جزئیات مجموعه را بازمی‌گرداند.
        """
        return reverse("posts:post-detail", kwargs={"slug": self.slug})


class PostManager(models.Manager):
    """
    EN: Custom manager for the Post model with optimized querysets.
    FA: مدیر (Manager) سفارشی برای مدل پست با QuerySetهای بهینه‌سازی شده.
    """

    def get_queryset(self):
        """
        EN: Returns a queryset with select_related, prefetch_related, and annotations.
        FA: یک QuerySet شامل select_related، prefetch_related و حاشیه‌نویسی‌ها بازمی‌گرداند.
        """
        from django.db.models import Count, Q
        from django.db.models.functions import Coalesce

        return (
            super()
            .get_queryset()
            .select_related("author", "category")
            .prefetch_related("tags")
            .annotate(
                comments_count=Coalesce(
                    Count("comments", filter=Q(comments__status="approved")), 0
                ),
                likes_count=Coalesce(
                    Count("reactions", filter=Q(reactions__reaction="like")), 0
                ),
            )
        )

    def published(self):
        """
        EN: Returns only the posts that have a 'published' status.
        FA: فقط پست‌هایی که در وضعیت 'منتشر شده' (published) هستند را بازمی‌گرداند.
        """
        return self.get_queryset().filter(status="published")

    def with_translations(self, lang_code="en"):
        """
        EN: Prefetches translations for the given language code and the default 'en'.
        FA: ترجمه‌ها را برای کد زبان داده شده و زبان پیش‌فرض 'en' پیش‌واکشی می‌کند.
        """
        from django.db.models import Prefetch

        return self.prefetch_related(
            Prefetch(
                "translations",
                queryset=PostTranslation.objects.filter(language_code=lang_code),
                to_attr="requested_translation",
            ),
            Prefetch(
                "translations",
                queryset=PostTranslation.objects.filter(language_code="en"),
                to_attr="default_translation",
            ),
        )


class Post(BaseModel):
    """
    EN:
    Core model representing a blog post.
    Handles status, scheduling, and various relations.
    Content is moved to PostTranslation model for localization.

    FA:
    مدل اصلی نشان‌دهنده یک پست بلاگ.
    وضعیت، زمان‌بندی و روابط مختلف را مدیریت می‌کند.
    محتوا برای بومی‌سازی به مدل PostTranslation منتقل شده است.
    """

    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("review", "Review"),
        ("scheduled", "Scheduled"),
        ("published", "Published"),
        ("archived", "Archived"),
    )
    VISIBILITY_CHOICES = (
        ("public", "Public"),
        ("private", "Private"),
        ("unlisted", "Unlisted"),
    )

    canonical_url = models.URLField(null=True, blank=True)
    is_hot = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    visibility = models.CharField(
        max_length=10, choices=VISIBILITY_CHOICES, default="public"
    )
    published_at = models.DateTimeField(null=True, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    author = models.ForeignKey(AuthorProfile, on_delete=models.CASCADE)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True
    )
    series = models.ForeignKey(Series, on_delete=models.SET_NULL, null=True, blank=True)
    cover_media = models.ForeignKey(
        "medias.Media",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="post_covers",
    )
    og_image = models.ForeignKey(
        "medias.Media",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="post_og_images",
    )
    views_count = models.PositiveIntegerField(default=0)
    tags = models.ManyToManyField(Tag, through="PostTag")
    related_posts = models.ManyToManyField("self", blank=True, symmetrical=False)
    reactions = GenericRelation(
        "interactions.Reaction",
        object_id_field="object_id",
        content_type_field="content_type",
    )

    objects = PostManager()

    class Meta:
        ordering = ["-published_at", "-id"]

    def __str__(self):
        """
        EN: Returns the ID and author of the post.
        FA: شناسه و نویسنده پست را بازمی‌گرداند.
        """
        return f"Post {self.id} by {self.author}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from .services import sync_post_media

        sync_post_media(self)

    @property
    def translation(self):
        """
        EN: Returns the requested translation or falls back to the default 'en' translation.
        FA: ترجمه درخواستی را برمی‌گرداند یا به ترجمه پیش‌فرض 'en' بازمی‌گردد.
        """
        if hasattr(self, "requested_translation") and self.requested_translation:
            return self.requested_translation[0]
        if hasattr(self, "default_translation") and self.default_translation:
            return self.default_translation[0]
        return (
            self.translations.filter(language_code="en").first()
            or self.translations.first()
        )


class PostTranslation(BaseModel):
    """
    EN: Stores localized content for a Post.
    FA: محتوای بومی‌سازی شده را برای یک پست ذخیره می‌کند.
    """

    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="translations"
    )
    language_code = models.CharField(max_length=10, db_index=True)
    slug = models.SlugField(max_length=255, allow_unicode=True)
    title = models.CharField(max_length=255)
    excerpt = models.TextField()
    short_description = models.TextField(blank=True, null=True)
    content = CKEditor5Field(config_name="default")
    reading_time_sec = models.PositiveIntegerField(default=0)
    seo_title = models.CharField(max_length=255, blank=True)
    seo_description = models.TextField(blank=True)

    class Meta:
        unique_together = (("post", "language_code"), ("slug", "language_code"))
        indexes = [
            models.Index(fields=["language_code", "slug"]),
        ]

    def __str__(self):
        """
        EN: Returns the title and language code.
        FA: عنوان و کد زبان را بازمی‌گرداند.
        """
        return f"{self.title} ({self.language_code})"

    def save(self, *args, **kwargs):
        """
        EN: Overrides save to calculate reading time and sync related media.
        FA: متد save را برای محاسبه زمان مطالعه و همگام‌سازی رسانه‌های مرتبط بازنویسی می‌کند.
        """
        if self.content:
            # EN: Simple reading time calculation based on word count.
            # FA: محاسبه ساده زمان مطالعه بر اساس تعداد کلمات.
            words = re.findall(r"\w+", self.content)
            word_count = len(words)
            reading_time_minutes = word_count / 200  # Average reading speed
            self.reading_time_sec = int(reading_time_minutes * 60)
        else:
            self.reading_time_sec = 0

        super().save(*args, **kwargs)
        from .services import sync_post_media

        # EN: Synchronize media mentioned in the content.
        # FA: همگام‌سازی رسانه‌های ذکر شده در محتوا.
        sync_post_media(self.post)  # Sync cover/OG images
        sync_post_media(self)  # Sync in-content media


class PostTag(BaseModel):
    """
    EN: Through model for the many-to-many relationship between Post and Tag.
    FA: مدل میانی برای رابطه چند‌به‌چند بین پست و برچسب.
    """

    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("post", "tag")


class Revision(BaseModel):
    """
    EN: Stores a historical revision of a post's content and metadata per language.
    FA: یک نسخه تاریخی از محتوا و متادیتای یک پست را به ازای هر زبان ذخیره می‌کند.
    """

    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    language_code = models.CharField(max_length=10, default="en")
    editor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    content = CKEditor5Field(config_name="default")
    title = models.CharField(max_length=255)
    excerpt = models.TextField()
    change_note = models.CharField(max_length=255, blank=True)

    def __str__(self):
        """
        EN: Returns a string representation identifying the post, language and the revision date.
        FA: نمایشی رشته‌ای شامل شناسایی پست، زبان و تاریخ بازنگری را بازمی‌گرداند.
        """
        return (
            f"Revision for {self.post.id} ({self.language_code}) at {self.created_at}"
        )


class PodcastCategory(BaseModel):
    """
    EN: Category for podcasts.
    FA: دسته‌بندی برای پادکست‌ها.
    """

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True)
    icon = models.FileField(upload_to="podcasts/categories/icons/", null=True, blank=True)

    class Meta:
        verbose_name_plural = "Podcast Categories"

    def __str__(self):
        return self.title


class Podcast(BaseModel):
    """
    EN: Core model representing a podcast episode (audio or video).
    FA: مدل اصلی نشان‌دهنده یک اپیزود پادکست (صوتی یا ویدیویی).
    """

    MEDIA_TYPE_CHOICES = (
        ("audio", "Audio"),
        ("video", "Video"),
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True)
    category = models.ForeignKey(
        PodcastCategory, on_delete=models.CASCADE, related_name="podcasts"
    )
    episode_number = models.PositiveIntegerField()
    cover_image = models.ImageField(upload_to="podcasts/covers/")
    audio_file = models.FileField(upload_to="podcasts/audio/", null=True, blank=True)
    media_type = models.CharField(
        max_length=10, choices=MEDIA_TYPE_CHOICES, default="audio"
    )
    video_file = models.FileField(upload_to="podcasts/video/", null=True, blank=True)
    video_url = models.URLField(blank=True, null=True)
    description = CKEditor5Field(config_name="default", blank=True)
    duration = models.PositiveIntegerField(help_text="Duration in minutes")
    published_date = models.DateTimeField()
    view_count = models.PositiveIntegerField(default=0)
    related_podcasts = models.ManyToManyField("self", blank=True, symmetrical=False)

    class Meta:
        ordering = ["-published_date", "-id"]

    def __str__(self):
        return f"Episode {self.episode_number}: {self.title}"


class GalleryItem(BaseModel):
    """
    EN: Represents an image item in a slider/list with Polaroid styling.
    FA: نشان‌دهنده یک آیتم تصویری در اسلایدر/لیست با استایل پولاروید.
    """

    image = models.ImageField(upload_to="gallery/")
    caption = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    link = models.URLField(blank=True, null=True)

    class Meta:
        ordering = ["order", "-id"]

    def __str__(self):
        return self.caption
