from django.contrib.auth.models import AbstractUser
from django.db import models

from common.fields import OptimizedImageField
from common.utils.files import get_sanitized_upload_path


class User(AbstractUser):
    profile_picture = OptimizedImageField(
        upload_to=get_sanitized_upload_path, null=True, blank=True
    )

    def __str__(self):
        return self.username

    @property
    def role(self):
        return [group.name for group in self.groups.all()]
