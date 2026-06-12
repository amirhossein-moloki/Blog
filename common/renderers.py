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
        if isinstance(data, dict) and all(
            key in data for key in ["data", "pagination", "messagesList"]
        ):
            return super().render(data, accepted_media_type, renderer_context)

        # EN: Wrap the data in the standardized structure if it's not already
        # FA: اگر داده‌ها در ساختار استاندارد نیستند، آن‌ها را بسته‌بندی کنید
        standardized_data = {
            "data": data,
            "pagination": {
                "pageNo": 1,
                "pageSize": 1000,
                "totalPage": 0,
                "totalCount": 0,
                "lastId": None,
            },
            "messagesList": [],
        }

        return super().render(standardized_data, accepted_media_type, renderer_context)
