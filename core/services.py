from typing import Any


class BaseService:
    """
    EN:
    Base class for all project services, providing a standardized structure for business logic.

    FA:
    کلاس پایه برای تمامی سرویس‌های پروژه که ساختار استانداردی را برای منطق کسب‌وکار فراهم می‌کند.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        EN: Initialize the service with optional arguments.
        FA: مقداردهی اولیه سرویس با آرگومان‌های اختیاری.
        """
        pass
