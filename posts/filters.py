from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from django_filters import rest_framework as filters

from .models import Post, Tag

HOT_POST_MAX_AGE_DAYS = 30
HOT_POST_MIN_VIEWS = 1000


class PostFilter(filters.FilterSet):
    """
    EN:
    Custom filter set for the Post model.
    Allows filtering by publication date range, category, tags, and a custom 'hot' post logic.

    FA:
    فیلتر ست سفارشی برای مدل پست.
    امکان فیلتر بر اساس بازه تاریخ انتشار، دسته‌بندی، برچسب‌ها و منطق سفارشی پست‌های 'داغ' (hot) را فراهم می‌کند.
    """

    published_after = filters.DateTimeFilter(
        field_name="published_at", lookup_expr="gte"
    )
    published_before = filters.DateTimeFilter(
        field_name="published_at", lookup_expr="lte"
    )
    category = filters.CharFilter(field_name="category__slug")
    tags = filters.ModelMultipleChoiceFilter(
        field_name="tags__slug",
        to_field_name="slug",
        queryset=Tag.objects.all(),
        conjoined=True,
    )
    is_hot = filters.BooleanFilter(method="filter_is_hot")

    def filter_is_hot(self, queryset, name, value):
        """
        EN: Filters posts based on 'hot' criteria: published recently and has high view count.
        FA: پست‌ها را بر اساس معیارهای 'داغ' بودن فیلتر می‌کند: اخیراً منتشر شده و تعداد بازدید بالایی دارد.
        """
        hot_post_criteria = Q(
            published_at__gte=timezone.now() - timedelta(days=HOT_POST_MAX_AGE_DAYS),
            views_count__gt=HOT_POST_MIN_VIEWS,
        )
        if value:
            return queryset.filter(hot_post_criteria)
        else:
            return queryset.exclude(hot_post_criteria)

    class Meta:
        model = Post
        fields = [
            "series",
            "visibility",
            "published_after",
            "published_before",
            "category",
            "tags",
        ]
