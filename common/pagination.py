from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CustomPagination(PageNumberPagination):
    """
    EN:
    Base pagination class that wraps data in a standardized response format.

    FA:
    کلاس پایه صفحه‌بندی که داده‌ها را در یک قالب پاسخ استاندارد بسته‌بندی می‌کند.
    """

    def get_paginated_response(self, data):
        """
        EN: Returns a standardized paginated response containing data and metadata.
        FA: یک پاسخ صفحه‌بندی شده استاندارد شامل داده‌ها و متا‌داده‌ها را بازمی‌گرداند.
        """
        return Response(
            {
                "data": data,
                "pagination": {
                    "pageNo": self.page.number,
                    "pageSize": self.page.paginator.per_page,
                    "totalPage": self.page.paginator.num_pages,
                    "totalCount": self.page.paginator.count,
                    "lastId": None,
                },
                "messagesList": [],
            }
        )


class CustomPageNumberPagination(CustomPagination):
    """
    EN: Standard page number pagination with configurable page size.
    FA: صفحه‌بندی استاندارد بر اساس شماره صفحه با قابلیت تنظیم اندازه صفحه.
    """

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100
