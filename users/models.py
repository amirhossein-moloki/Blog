from django.contrib.auth.models import AbstractUser

from common.fields import OptimizedImageField
from common.utils.files import get_sanitized_upload_path


class User(AbstractUser):
    """
    EN:
    Custom User model extending the default Django AbstractUser.
    Includes a profile picture with automatic optimization.

    FA:
    مدل کاربر سفارشی که کلاس AbstractUser پیش‌فرض جنگو را گسترش می‌دهد.
    شامل تصویر پروفایل با قابلیت بهینه‌سازی خودکار است.
    """

    profile_picture = OptimizedImageField(
        upload_to=get_sanitized_upload_path, null=True, blank=True
    )

    def __str__(self):
        """
        EN: Returns the username as the string representation of the user.
        FA: نام کاربری را به عنوان نمایش رشته‌ای کاربر بازمی‌گرداند.
        """
        return self.username

    @property
    def role(self):
        """
        EN: Returns a list of names for all groups the user belongs to.
        FA: لیستی از نام تمامی گروه‌هایی که کاربر عضو آن‌هاست بازمی‌گرداند.
        """
        return [group.name for group in self.groups.all()]
