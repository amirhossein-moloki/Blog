class FileChangeDetectionMixin:
    """
    EN:
    A mixin that detects changes to a specified file field on a model instance.
    To use, inherit this mixin in your model and set the `MONITORED_FILE_FIELD`
    attribute to the name of the file field you want to track.

    FA:
    یک Mixin که تغییرات یک فیلد فایل مشخص شده را در نمونه مدل تشخیص می‌دهد.
    برای استفاده، این Mixin را در مدل خود ارث‌بری کرده و ویژگی `MONITORED_FILE_FIELD`
    را به نام فیلد فایلی که می‌خواهید ردیابی کنید، تنظیم کنید.
    """

    # EN: Note: This mixin's logic is bypassed by bulk operations like QuerySet.update().
    # FA: نکته: منطق این Mixin توسط عملیات گروهی مانند QuerySet.update() نادیده گرفته می‌شود.

    MONITORED_FILE_FIELD = None

    def __init__(self, *args, **kwargs):
        """
        EN: Initializes the mixin and captures the original file name.
        FA: Mixin را مقداردهی اولیه کرده و نام اصلی فایل را ثبت می‌کند.
        """
        super().__init__(*args, **kwargs)
        if self.MONITORED_FILE_FIELD:
            field_file = getattr(self, self.MONITORED_FILE_FIELD, None)
            self._original_file_name = field_file.name if field_file else None

    def save(self, *args, **kwargs):
        """
        EN: Overrides the save method to detect if the monitored file has changed.
        FA: متد save را بازنویسی می‌کند تا تشخیص دهد آیا فایل تحت نظارت تغییر کرده است یا خیر.
        """
        image_changed = False
        update_fields = kwargs.get("update_fields")
        is_new = self._state.adding

        if self.MONITORED_FILE_FIELD:
            field_file = getattr(self, self.MONITORED_FILE_FIELD, None)
            current_file_name = field_file.name if field_file else None

            # EN: If update_fields is specified, only check for changes if the monitored field is included
            # FA: اگر update_fields مشخص شده باشد، فقط در صورتی تغییرات بررسی می‌شود که فیلد تحت نظارت در آن باشد
            if update_fields is None or self.MONITORED_FILE_FIELD in update_fields:
                if is_new and current_file_name:
                    image_changed = True
                elif not is_new and self._original_file_name != current_file_name:
                    image_changed = True

        self._image_changed = image_changed

        super().save(*args, **kwargs)

        if self.MONITORED_FILE_FIELD:
            # EN: After saving, update the original file name to the current one
            # FA: پس از ذخیره، نام اصلی فایل را به نام فعلی به‌روزرسانی می‌کند
            field_file = getattr(self, self.MONITORED_FILE_FIELD, None)
            self._original_file_name = field_file.name if field_file else None

    @property
    def image_has_changed(self):
        """
        EN: Property to check if the image has changed during the last save.
        FA: ویژگی برای بررسی اینکه آیا تصویر در طول آخرین ذخیره‌سازی تغییر کرده است یا خیر.
        """
        return getattr(self, "_image_changed", False)


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
