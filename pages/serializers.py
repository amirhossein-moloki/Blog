from rest_framework import serializers

from .models import Page


class PageSerializer(serializers.ModelSerializer):
    """
    EN: Serializer for the Page model, providing all fields for individual pages.
    FA: سریالایزر برای مدل صفحه (Page)، که تمامی فیلدها را برای صفحات تکی فراهم می‌کند.
    """

    class Meta:
        model = Page
        fields = "__all__"
