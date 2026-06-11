import shortuuid
from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.db.models.signals import post_save
from phonenumber_field.modelfields import PhoneNumberField

from common.fields import OptimizedImageField
from common.utils.files import get_sanitized_upload_path


class User(AbstractUser):
    phone_number = PhoneNumberField(unique=True, null=True, blank=True)
    profile_picture = OptimizedImageField(
        upload_to=get_sanitized_upload_path, null=True, blank=True
    )
    is_phone_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.username

    @property
    def role(self):
        return [group.name for group in self.groups.all()]
