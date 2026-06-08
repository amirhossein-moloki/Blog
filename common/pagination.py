from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class CustomPagination(PageNumberPagination):
    def get_paginated_response(self, data):
        return Response({
            "data": data,
            "pagination": {
                "pageNo": self.page.number,
                "pageSize": self.page.paginator.per_page,
                "totalPage": self.page.paginator.num_pages,
                "totalCount": self.page.paginator.count,
                "lastId": None
            },
            "messagesList": []
        })
