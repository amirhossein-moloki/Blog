from django.db import models

from core.base_models import BaseModel


class Menu(BaseModel):
    """
    EN:
    Represents a navigation menu (e.g., Header, Footer).
    Menus are defined by their location in the layout.

    FA:
    نشان‌دهنده یک منوی پیمایش (مانند هدر، فوتر).
    منوها بر اساس مکان قرارگیری‌شان در چیدمان تعریف می‌شوند.
    """

    LOCATION_CHOICES = (
        ("header", "Header"),
        ("footer", "Footer"),
        ("sidebar", "Sidebar"),
    )
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=10, choices=LOCATION_CHOICES, unique=True)

    def __str__(self):
        """
        EN: Returns the name of the menu.
        FA: نام منو را بازمی‌گرداند.
        """
        return self.name


class MenuItem(BaseModel):
    """
    EN:
    Represents an individual link within a Menu.
    Supports hierarchical structures (parent/child items).

    FA:
    نشان‌دهنده یک لینک تکی داخل یک منو.
    از ساختارهای سلسله‌مراتبی (آیتم‌های والد/فرزند) پشتیبانی می‌کند.
    """

    menu = models.ForeignKey(Menu, on_delete=models.CASCADE)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    label = models.CharField(max_length=255)
    url = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    target_blank = models.BooleanField(default=False)

    def __str__(self):
        """
        EN: Returns the label of the menu item.
        FA: برچسب آیتم منو را بازمی‌گرداند.
        """
        return self.label
