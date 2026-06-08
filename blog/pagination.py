from common.pagination import CustomPagination

class CustomPageNumberPagination(CustomPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
