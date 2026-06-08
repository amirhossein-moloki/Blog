import shortuuid
from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.db.models.signals import post_save
from phonenumber_field.modelfields import PhoneNumberField
from common.fields import OptimizedImageField
from common.utils.files import get_sanitized_upload_path


class User(AbstractUser):
    phone_number = PhoneNumberField(unique=True)
    profile_picture = OptimizedImageField(
        upload_to=get_sanitized_upload_path, null=True, blank=True
    )
    is_phone_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.username

    @property
    def role(self):
        return [group.name for group in self.groups.all()]


from django.utils import timezone
from datetime import timedelta

from django.utils import timezone
from datetime import timedelta

class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    identifier = models.CharField(max_length=255)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.identifier} - {self.code}"

    def save(self, *args, **kwargs):
        if not self.pk:
            self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
