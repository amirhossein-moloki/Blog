from unittest.mock import MagicMock

from django.test import TestCase

from common.pagination import CustomPagination
from common.renderers import StandardResponseRenderer


class PaginationTests(TestCase):
    def test_custom_pagination_response_structure(self):
        paginator = CustomPagination()
        paginator.page = MagicMock()
        paginator.page.number = 1
        paginator.page.paginator.per_page = 10
        paginator.page.paginator.num_pages = 5
        paginator.page.paginator.count = 50

        data = [{"id": 1}, {"id": 2}]
        response = paginator.get_paginated_response(data)

        self.assertEqual(response.data["data"], data)
        self.assertEqual(response.data["pagination"]["pageNo"], 1)
        self.assertEqual(response.data["pagination"]["totalCount"], 50)
        self.assertEqual(response.data["messagesList"], [])


class RendererTests(TestCase):
    def test_standard_response_renderer(self):
        renderer = StandardResponseRenderer()
        data = {"key": "value"}
        rendered = renderer.render(data)

        import json

        decoded = json.loads(rendered)

        self.assertEqual(decoded["data"], data)
        self.assertNotIn("pagination", decoded)
        self.assertIn("messagesList", decoded)

    def test_standard_response_renderer_with_pagination(self):
        renderer = StandardResponseRenderer()
        data = {
            "data": [{"id": 1}],
            "pagination": {"pageNo": 1},
        }
        rendered = renderer.render(data)

        import json

        decoded = json.loads(rendered)

        self.assertEqual(decoded["data"], [{"id": 1}])
        self.assertEqual(decoded["pagination"], {"pageNo": 1})
        self.assertIn("messagesList", decoded)

    def test_standard_response_renderer_already_standardized(self):
        renderer = StandardResponseRenderer()
        data = {
            "data": {"key": "value"},
            "messagesList": [],
        }
        rendered = renderer.render(data)

        import json

        decoded = json.loads(rendered)
        self.assertEqual(decoded, data)
