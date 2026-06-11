from django.test import TestCase

from core.base_models import BaseModel


class CoreModelTest(TestCase):
    def test_base_fields(self):
        self.assertTrue(hasattr(BaseModel, "is_active"))
        self.assertTrue(hasattr(BaseModel, "created_at"))
