from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from django_filters import rest_framework as filters

from .models import Article, Tag

HOT_ARTICLE_MAX_AGE_DAYS = 30
HOT_ARTICLE_MIN_VIEWS = 1000


class ArticleFilter(filters.FilterSet):
    """
    EN:
    Custom filter set for the Article model.
    Allows filtering by publication date range, category, tags, and a custom 'hot' article logic.

    FA:
    فیلتر ست سفارشی برای مدل مقاله.
    امکان فیلتر بر اساس بازه تاریخ انتشار، دسته‌بندی، برچسب‌ها و منطق سفارشی مقاله‌های 'داغ' (hot) را فراهم می‌کند.
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
        EN: Filters articles based on explicit editorial 'is_hot' flag or high recent engagement.
        FA: مقاله‌ها را بر اساس پرچم سردبیری 'is_hot' یا معیارهای بازدید و انتشار اخیر فیلتر می‌کند.
        """
        if value is None:
            return queryset
        hot_article_criteria = Q(is_hot=True) | Q(
            published_at__gte=timezone.now() - timedelta(days=HOT_ARTICLE_MAX_AGE_DAYS),
            views_count__gt=HOT_ARTICLE_MIN_VIEWS,
        )
        if value:
            return queryset.filter(hot_article_criteria)
        return queryset.exclude(hot_article_criteria)

    class Meta:
        model = Article
        fields = [
            "series",
            "visibility",
            "published_after",
            "published_before",
            "category",
            "tags",
        ]
