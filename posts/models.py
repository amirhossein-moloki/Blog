import re

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.urls import reverse
from django_ckeditor_5.fields import CKEditor5Field

from core.base_models import BaseModel

User = get_user_model()


class AuthorProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    display_name = models.CharField(max_length=255)
    bio = models.TextField(blank=True)
    avatar = models.ForeignKey(
        "medias.Media", on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return self.display_name


class Category(BaseModel):
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

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Tag(BaseModel):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Series(BaseModel):
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
        return self.title

    def get_absolute_url(self):
        return reverse("posts:post-detail", kwargs={"slug": self.slug})


class PostManager(models.Manager):
    def get_queryset(self):
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
        return self.get_queryset().filter(status="published")


class Post(BaseModel):
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

    slug = models.SlugField(unique=True, allow_unicode=False)
    canonical_url = models.URLField(null=True, blank=True)
    title = models.CharField(max_length=255)
    excerpt = models.TextField()
    is_hot = models.BooleanField(default=False)
    content = CKEditor5Field(config_name="default")
    reading_time_sec = models.PositiveIntegerField(default=0)
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
    seo_title = models.CharField(max_length=255, blank=True)
    seo_description = models.TextField(blank=True)
    og_image = models.ForeignKey(
        "medias.Media",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="post_og_images",
    )
    views_count = models.PositiveIntegerField(default=0)
    tags = models.ManyToManyField(Tag, through="PostTag")
    reactions = GenericRelation(
        "interactions.Reaction",
        object_id_field="object_id",
        content_type_field="content_type",
    )

    objects = PostManager()

    class Meta:
        ordering = ["-published_at", "-id"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.content:
            words = re.findall(r"\w+", self.content)
            word_count = len(words)
            reading_time_minutes = word_count / 200  # Average reading speed
            self.reading_time_sec = int(reading_time_minutes * 60)
        else:
            self.reading_time_sec = 0

        super().save(*args, **kwargs)
        from .services import sync_post_media

        sync_post_media(self)


class PostTag(BaseModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("post", "tag")


class Revision(BaseModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    editor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    content = CKEditor5Field(config_name="default")
    title = models.CharField(max_length=255)
    excerpt = models.TextField()
    change_note = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Revision for {self.post.title} at {self.created_at}"
