class DynamicFieldsMixin:
    """
    EN:
    A serializer mixin that takes an additional `fields` argument that controls
    which fields should be displayed.

    FA:
    یک Mixin سریالایزر که یک آرگومان اضافی `fields` دریافت می‌کند تا فیلدهای
    نمایش داده شده را کنترل کند.
    """

    def __init__(self, *args, **kwargs):
        """
        EN: Initializes the serializer and filters fields based on the 'fields' argument.
        FA: سریالایزر را مقداردهی اولیه کرده و فیلدها را بر اساس آرگومان 'fields' فیلتر می‌کند.
        """
        # EN: Don't pass the 'fields' arg up to the superclass
        # FA: آرگومان 'fields' را به کلاس والد منتقل نکنید
        fields = kwargs.pop("fields", None)

        # EN: Instantiate the superclass normally
        # FA: کلاس والد را به طور معمول نمونه‌سازی کنید
        super().__init__(*args, **kwargs)

        if fields is not None:
            # EN: Drop any fields that are not specified in the `fields` argument.
            # FA: هر فیلدی که در آرگومان `fields` مشخص نشده است را حذف کنید.
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


class DynamicSerializerViewMixin:
    """
    EN:
    A view mixin that extracts 'fields' from query parameters and passes them to the serializer.

    FA:
    یک Mixin برای View که 'fields' را از پارامترهای کوئری استخراج کرده و به سریالایزر منتقل می‌کند.
    """

    def get_serializer(self, *args, **kwargs):
        """
        EN: Overrides get_serializer to inject the 'fields' argument from the request.
        FA: متد get_serializer را بازنویسی می‌کند تا آرگومان 'fields' را از درخواست تزریق کند.
        """
        serializer_class = self.get_serializer_class()
        kwargs.setdefault("context", self.get_serializer_context())

        if self.request.method == "GET":
            fields_query = self.request.query_params.get("fields")
            if fields_query:
                # EN: Convert comma-separated string to a tuple of field names.
                # FA: تبدیل رشته جدا شده با کاما به یک tuple از نام فیلدها.
                fields = tuple(f.strip() for f in fields_query.split(","))
                kwargs["fields"] = fields

        return serializer_class(*args, **kwargs)
