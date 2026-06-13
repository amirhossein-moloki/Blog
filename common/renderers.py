from rest_framework.renderers import JSONRenderer


class StandardResponseRenderer(JSONRenderer):
    """
    EN:
    A custom JSON renderer that ensures all API responses follow a standardized format.
    The format includes 'data', 'pagination', and 'messagesList'.

    FA:
    یک نمایش‌دهنده (Renderer) JSON سفارشی که اطمینان حاصل می‌کند تمامی پاسخ‌های API از یک قالب استاندارد پیروی می‌کنند.
    این قالب شامل 'data'، 'pagination' و 'messagesList' است.
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        EN: Renders the response data into a standardized JSON structure.
        FA: داده‌های پاسخ را در یک ساختار JSON استاندارد نمایش می‌دهد.
        """
        # EN: Check if the response is already in the standardized structure
        # FA: بررسی اینکه آیا پاسخ در حال حاضر در ساختار استاندارد هست یا خیر
        # EN: We now only require 'data' and 'messagesList' to consider it standardized.
        # FA: اکنون فقط به 'data' و 'messagesList' نیاز داریم تا آن را استاندارد در نظر بگیریم.
        if isinstance(data, dict) and "data" in data and "messagesList" in data:
            return super().render(data, accepted_media_type, renderer_context)

        # EN: Wrap the data in the standardized structure if it's not already
        # FA: اگر داده‌ها در ساختار استاندارد نیستند، آن‌ها را بسته‌بندی کنید
        # EN: We no longer include a default 'pagination' object here.
        # FA: ما دیگر در اینجا یک شیء 'pagination' پیش‌فرض قرار نمی‌دهیم.
        standardized_data = {
            "data": data,
            "messagesList": [],
        }

        # EN: If data is a dict and contains pagination, preserve it.
        # FA: اگر داده یک دیکشنری است و شامل صفحه‌بندی است، آن را حفظ کنید.
        if isinstance(data, dict) and "pagination" in data:
            standardized_data["pagination"] = data.get("pagination")
            # EN: If it also has data or messagesList, use them.
            # FA: اگر دارای data یا messagesList هم هست، از آن‌ها استفاده کنید.
            if "data" in data:
                standardized_data["data"] = data.get("data")
            if "messagesList" in data:
                standardized_data["messagesList"] = data.get("messagesList")

        return super().render(standardized_data, accepted_media_type, renderer_context)
