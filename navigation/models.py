from django.db import models

from core.base_models import BaseModel


class Menu(BaseModel):
    LOCATION_CHOICES = (
        ("header", "Header"),
        ("footer", "Footer"),
        ("sidebar", "Sidebar"),
    )
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=10, choices=LOCATION_CHOICES, unique=True)

    def __str__(self):
        return self.name


class MenuItem(BaseModel):
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    label = models.CharField(max_length=255)
    url = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    target_blank = models.BooleanField(default=False)

    def __str__(self):
        return self.label
