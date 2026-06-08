from rest_framework.renderers import JSONRenderer

class StandardResponseRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        # Check if the response is already in the standardized structure
        if isinstance(data, dict) and all(key in data for key in ["data", "pagination", "messagesList"]):
            return super().render(data, accepted_media_type, renderer_context)

        # Wrap the data in the standardized structure
        standardized_data = {
            "data": data,
            "pagination": {
                "pageNo": 1,
                "pageSize": 1000,
                "totalPage": 0,
                "totalCount": 0,
                "lastId": None
            },
            "messagesList": []
        }

        return super().render(standardized_data, accepted_media_type, renderer_context)
