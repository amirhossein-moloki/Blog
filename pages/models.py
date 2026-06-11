from django.db import models
from django_ckeditor_5.fields import CKEditor5Field

from core.base_models import BaseModel


class Page(BaseModel):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("review", "Review"),
        ("scheduled", "Scheduled"),
        ("published", "Published"),
        ("archived", "Archived"),
    )
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=255)
    content = CKEditor5Field(config_name="default")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    published_at = models.DateTimeField(null=True, blank=True)
    seo_title = models.CharField(max_length=255, blank=True)
    seo_description = models.TextField(blank=True)

    def __str__(self):
        return self.title
