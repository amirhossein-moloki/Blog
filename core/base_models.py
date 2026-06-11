from django.db import models
from django.utils.translation import gettext_lazy as _


class BaseModel(models.Model):
    """
    مدل پایه انتزاعی که فیلدهای مشترک را برای تمام مدل‌ها فراهم می‌کند.
    Abstract base model providing common fields for all models.
    """

    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is Active"),
        help_text=_("مشخص می‌کند که آیا این رکورد فعال است یا خیر."),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
        help_text=_("زمان ایجاد رکورد."),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At"),
        help_text=_("زمان آخرین بروزرسانی رکورد."),
    )

    class Meta:
        abstract = True
