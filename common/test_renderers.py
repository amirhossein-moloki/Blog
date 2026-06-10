from django.test import TestCase
from common.renderers import StandardResponseRenderer
import json

class StandardResponseRendererTest(TestCase):
    def setUp(self):
        self.renderer = StandardResponseRenderer()

    def test_render_wraps_data(self):
        data = {"foo": "bar"}
        response = self.renderer.render(data)
        decoded = json.loads(response)
        self.assertEqual(decoded["data"], data)
        self.assertIn("pagination", decoded)
        self.assertIn("messagesList", decoded)

    def test_render_does_not_double_wrap(self):
        data = {
            "data": "already",
            "pagination": {"pageNo": 1},
            "messagesList": []
        }
        response = self.renderer.render(data)
        decoded = json.loads(response)
        self.assertEqual(decoded, data)
