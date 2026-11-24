"""
EN: Custom DRF search filter with Persian/Arabic character, numeral, and ZWNJ normalization.
FA: فیلتر جست‌وجوی سفارشی DRF با پشتیبانی از یکسان‌سازی فارسی/عربی، ارقام و نیم‌فاصله.
"""

from __future__ import annotations

import operator
from functools import reduce

from django.db.models import Q
from rest_framework.filters import SearchFilter

from common.utils.search_text import build_persian_arabic_variants


class NormalizedSearchFilter(SearchFilter):
    """
    EN: Expands each search term into normalized Persian/Arabic/digit/ZWNJ variants before matching search_fields.
    FA: هر واژه جست‌وجو را به نگارش‌های جایگزین فارسی/عربی/ارقام/نیم‌فاصله بسط می‌دهد تا نتایج دقیق‌تر شوند.
    """

    def filter_queryset(self, request, queryset, view):
        search_fields = self.get_search_fields(view, request)
        search_terms = self.get_search_terms(request)

        if not search_fields or not search_terms:
            return queryset

        orm_lookups = [
            self.construct_search(str(search_field)) for search_field in search_fields
        ]

        conditions = []
        for search_term in search_terms:
            variants = build_persian_arabic_variants(search_term)
            if not variants:
                continue

            term_queries = [
                Q(**{orm_lookup: variant})
                for orm_lookup in orm_lookups
                for variant in variants
            ]
            if term_queries:
                conditions.append(reduce(operator.or_, term_queries))

        if not conditions:
            return queryset

        queryset = queryset.filter(reduce(operator.and_, conditions))

        if self.must_call_distinct(queryset, orm_lookups):
            # Preserve queryset ordering while deduplicating M2M/translation joins.
            queryset = queryset.distinct()

        return queryset
