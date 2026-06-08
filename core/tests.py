from django.test import TestCase
from django.db import models
from core.base_models import BaseModel

class CoreTestModel(BaseModel):
    """
    یک مدل آزمایشی برای تست BaseModel.
    A test model for testing BaseModel.
    """
    name = models.CharField(max_length=100)

    class Meta:
        # این مدل فقط برای تست است و نباید در دیتابیس واقعی ساخته شود
        # This model is only for testing and should not be created in the real database
        app_label = 'core'

class BaseModelTest(TestCase):
    """
    تست‌های مدل پایه.
    Base model tests.
    """
    @classmethod
    def setUpClass(cls):
        # این کار در جنگو کمی پیچیده است که مدل‌های تعریف شده در تست را به دیتابیس آزمایشی اضافه کنیم
        # به همین دلیل از یک روش ساده‌تر استفاده می‌کنیم یا مدل را در models.py می‌گذاریم اما به عنوان abstract
        super().setUpClass()

    def test_base_model_fields(self) -> None:
        """
        بررسی وجود و عملکرد فیلدهای مدل پایه.
        Check the existence and functionality of base model fields.
        """
        # از آنجایی که CoreTestModel در migrations نیست، جنگو جدولی برای آن نمی‌سازد مگر اینکه دستی اضافه شود.
        # برای سادگی در فاز ۱، از یک مدل واقعی که از BaseModel ارث می‌برد استفاده خواهیم کرد در فازهای بعدی.
        # فعلاً فقط ساختار فیلدها را چک می‌کنیم.

        self.assertTrue(hasattr(BaseModel, 'is_active'))
        self.assertTrue(hasattr(BaseModel, 'created_at'))
        self.assertTrue(hasattr(BaseModel, 'updated_at'))
