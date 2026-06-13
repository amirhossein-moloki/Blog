from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import inline_serializer
from rest_framework import serializers


class StandardizedAutoSchema(AutoSchema):
    """
    EN:
    Custom OpenAPI schema generator for drf-spectacular.
    It automatically wraps all 2xx response serializers in the project's standardized structure.

    FA:
    تولیدکننده شمای سفارشی OpenAPI برای drf-spectacular.
    این کلاس به طور خودکار تمامی سریالایزرهای پاسخ 2xx را در ساختار استاندارد پروژه بسته‌بندی می‌کند.
    """

    def get_response_serializers(self):
        """
        EN: Overrides the default response serializer discovery to apply wrapping.
        FA: شناسایی سریالایزر پاسخ پیش‌فرض را برای اعمال بسته‌بندی بازنویسی می‌کند.
        """
        serializers_dict = super().get_response_serializers()

        # EN: Check if we're already inside a wrapped serializer to prevent recursion
        # FA: بررسی اینکه آیا در حال حاضر داخل یک سریالایزر بسته‌بندی شده هستیم تا از بازگشت چرخه‌ای جلوگیری شود
        if getattr(self, "_is_wrapping", False):
            return serializers_dict

        self._is_wrapping = True
        try:
            if isinstance(serializers_dict, dict):
                # EN: Wrap each response serializer in the standardized format
                # FA: بسته‌بندی هر سریالایزر پاسخ در قالب استاندارد
                for status_code, serializer in serializers_dict.items():
                    if status_code.startswith("2"):  # Only wrap successful responses
                        serializers_dict[status_code] = self._wrap_in_standard_format(
                            serializer, status_code
                        )
            else:
                # EN: It's a single serializer (typical for 200 OK)
                # FA: این یک سریالایزر واحد است (معمولاً برای 200 OK)
                serializers_dict = self._wrap_in_standard_format(
                    serializers_dict, "200"
                )
        finally:
            self._is_wrapping = False

        return serializers_dict

    def _wrap_in_standard_format(self, serializer, status_code):
        """
        EN: Wraps a given serializer in an inline serializer that matches the standard response format.
        FA: یک سریالایزر داده شده را در یک سریالایزر داخلی که با قالب پاسخ استاندارد مطابقت دارد، بسته‌بندی می‌کند.
        """
        # EN: Determine a unique name for the wrapped serializer
        # FA: تعیین یک نام منحصر به فرد برای سریالایزر بسته‌بندی شده
        if hasattr(serializer, "__name__"):
            serializer_name = serializer.__name__
        elif hasattr(serializer, "__class__"):
            serializer_name = serializer.__class__.__name__
        else:
            serializer_name = "Data"

        # EN: Use view name and method to make it unique and avoid collisions
        # FA: استفاده از نام view و متد برای منحصر به فرد کردن آن و جلوگیری از تداخل
        view_name = self.view.__class__.__name__
        if view_name.endswith("ViewSet"):
            view_name = view_name[:-7]

        method_name = self.method.capitalize()

        # EN: Add action if available (for ViewSets)
        # FA: اضافه کردن action در صورت موجود بودن (برای ViewSetها)
        action_name = getattr(self.view, "action", "").capitalize()

        # EN: Ensure name starts with a letter and is alphanumeric
        # FA: اطمینان از اینکه نام با حرف شروع شده و الفبایی-عددی باشد
        name = f"Std{view_name}{action_name}{method_name}{serializer_name}{status_code}"

        # EN: Prepare fields for the standardized response
        # FA: آماده‌سازی فیلدها برای پاسخ استاندارد
        fields = {
            "data": serializer,
            "messagesList": serializers.ListField(
                child=serializers.CharField(), default=[]
            ),
        }

        # EN: pagination fields should only be present if the view is paginated
        # FA: فیلدهای صفحه‌بندی فقط باید در صورتی وجود داشته باشند که view صفحه‌بندی شده باشد
        include_pagination = False
        if status_code.startswith("2"):
            # EN: Detect list-like responses which are typically paginated
            # FA: شناسایی پاسخ‌های شبیه لیست که معمولاً صفحه‌بندی می‌شوند
            is_list_response = (
                getattr(self.view, "action", None) == "list"
                or isinstance(serializer, serializers.ListSerializer)
                or getattr(serializer, "many", False)
            )

            # EN: Check if the view is configured for pagination
            # FA: بررسی اینکه آیا view برای صفحه‌بندی پیکربندی شده است
            has_pagination = getattr(self.view, "pagination_class", None) is not None

            if is_list_response and has_pagination:
                include_pagination = True

            # EN: Handle specific cases or manual overrides if needed
            # FA: مدیریت موارد خاص یا بازنویسی‌های دستی در صورت نیاز
            action_name = getattr(self.view, "action", "")
            if action_name in ["same_category", "related_posts"]:
                include_pagination = True

        if include_pagination:
            pagination_fields = {
                "pageNo": serializers.IntegerField(default=1),
                "pageSize": serializers.IntegerField(default=10),
                "totalPage": serializers.IntegerField(default=1),
                "totalCount": serializers.IntegerField(default=1),
                "lastId": serializers.CharField(allow_null=True, default=None),
            }
            fields["pagination"] = inline_serializer(
                name=f"Pag{name}", fields=pagination_fields
            )

        return inline_serializer(
            name=name,
            fields=fields,
        )
