from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field

from core.base_models import BaseModel

User = get_user_model()


class Comment(BaseModel):
    """
    EN:
    Represents a user comment on a post.
    Supports nested replies and moderation statuses.

    FA:
    نشان‌دهنده نظر یک کاربر روی یک پست.
    از پاسخ‌های تو در تو و وضعیت‌های نظارت (Moderation) پشتیبانی می‌کند.
    """

    class Meta:
        ordering = ["-created_at"]

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("spam", "Spam"),
        ("removed", "Removed"),
    )
    post = models.ForeignKey(
        "posts.Post", on_delete=models.CASCADE, related_name="comments"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies"
    )
    content = CKEditor5Field(config_name="default")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    reactions = GenericRelation(
        "Reaction", object_id_field="object_id", content_type_field="content_type"
    )

    def __str__(self):
        """
        EN: Returns a string representation of the comment creator and the post ID.
        FA: نمایشی رشته‌ای از ایجادکننده نظر و شناسه پست را بازمی‌گرداند.
        """
        return f"Comment by {self.user} on {self.post_id}"


class Reaction(BaseModel):
    """
    EN:
    Represents a user reaction (e.g., like, emoji) to any content type.
    Uses Generic Foreign Key to relate to Posts, Comments, or other models.

    FA:
    نشان‌دهنده واکنش کاربر (مانند لایک، اموجی) به هر نوع محتوایی.
    از Generic Foreign Key برای ارتباط با پست‌ها، نظرات یا مدل‌های دیگر استفاده می‌کند.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reaction = models.CharField(
        max_length=50
    )  # EN: like|emoji_code | FA: لایک یا کد اموجی

    # EN: Generic Foreign Key setup
    # FA: تنظیمات Generic Foreign Key
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        unique_together = ("user", "content_type", "object_id", "reaction")

    def __str__(self):
        """
        EN: Returns a string representation of the user reaction and target object.
        FA: نمایشی رشته‌ای از واکنش کاربر و شیء هدف را بازمی‌گرداند.
        """
        return f"{self.user}'s {self.reaction} on {self.content_object}"
