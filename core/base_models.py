from django.db import models
from django.utils.translation import gettext_lazy as _


class BaseModel(models.Model):
    """
    EN:
    Abstract base model providing common fields for all models in the project.

    FA:
    مدل پایه انتزاعی که فیلدهای مشترک برای تمامی مدل‌های پروژه را فراهم می‌کند.
    """

    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is Active"),
        help_text=_("Specifies whether this record is active or not."),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
        help_text=_("The time the record was created."),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At"),
        help_text=_("The time of the last update to the record."),
    )

    class Meta:
        abstract = True
