from django.contrib.auth import get_user_model
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from core.base_models import BaseModel

User = get_user_model()


class Media(BaseModel):
    storage_key = models.CharField(max_length=255)
    url = models.URLField()
    type = models.CharField(max_length=50)  # image/video/audio/file
    mime = models.CharField(max_length=100)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    duration = models.PositiveIntegerField(null=True, blank=True)  # in seconds
    size_bytes = models.PositiveIntegerField(default=0)
    alt_text = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.title or self.storage_key

    def get_download_url(self):
        if self.pk:
            return reverse("medias:download_media", kwargs={"media_id": self.pk})
        return ""


class PostMedia(BaseModel):
    post = models.ForeignKey(
        "posts.Post", on_delete=models.CASCADE, related_name="media_attachments"
    )
    media = models.ForeignKey(
        Media, on_delete=models.CASCADE, related_name="post_attachments"
    )
    attachment_type = models.CharField(
        max_length=50, default="in-content"
    )  # e.g., 'in-content', 'cover', 'og-image'

    class Meta:
        unique_together = ("post", "media", "attachment_type")
        verbose_name = _("Post Media")
        verbose_name_plural = _("Post Media")

    def __str__(self):
        return f"{self.media.title} attached to post {self.post_id} as {self.attachment_type}"
