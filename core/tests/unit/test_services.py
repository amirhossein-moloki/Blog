from django.test import TestCase

from core.services import BaseService


class BaseServiceTest(TestCase):
    def test_base_service_init(self):
        service = BaseService()
        self.assertIsInstance(service, BaseService)

        service_with_args = BaseService("arg", kwarg="value")
        self.assertIsInstance(service_with_args, BaseService)
