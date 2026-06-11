from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field

from core.base_models import BaseModel

User = get_user_model()


class Comment(BaseModel):
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
        return f"Comment by {self.user} on {self.post_id}"


class Reaction(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reaction = models.CharField(max_length=50)  # like|emoji_code

    # Generic Foreign Key setup
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        unique_together = ("user", "content_type", "object_id", "reaction")

    def __str__(self):
        return f"{self.user}'s {self.reaction} on {self.content_object}"
