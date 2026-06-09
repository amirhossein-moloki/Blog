from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

class StandardizedAutoSchema(AutoSchema):
    def get_response_serializers(self):
        serializers_dict = super().get_response_serializers()

        # Check if we're already inside a wrapped serializer to prevent recursion
        if getattr(self, '_is_wrapping', False):
            return serializers_dict

        self._is_wrapping = True
        try:
            if isinstance(serializers_dict, dict):
                # Wrap each response serializer in the standardized format
                for status_code, serializer in serializers_dict.items():
                    if status_code.startswith('2'): # Only wrap successful responses
                        serializers_dict[status_code] = self._wrap_in_standard_format(serializer, status_code)
            else:
                # It's a single serializer (typical for 200 OK)
                serializers_dict = self._wrap_in_standard_format(serializers_dict, '200')
        finally:
            self._is_wrapping = False

        return serializers_dict

    def _wrap_in_standard_format(self, serializer, status_code):
        # Determine a unique name for the wrapped serializer
        if hasattr(serializer, "__name__"):
            serializer_name = serializer.__name__
        elif hasattr(serializer, "__class__"):
            serializer_name = serializer.__class__.__name__
        else:
            serializer_name = "Data"

        # Use view name and method to make it unique and avoid collisions
        view_name = self.view.__class__.__name__
        if view_name.endswith('ViewSet'):
            view_name = view_name[:-7]

        method_name = self.method.capitalize()

        # Add action if available (for ViewSets)
        action_name = getattr(self.view, 'action', '').capitalize()

        # Ensure name starts with a letter and is alphanumeric
        name = f"Std{view_name}{action_name}{method_name}{serializer_name}{status_code}"

        # pagination fields should only be present if the view is paginated
        pagination_fields = {
            "pageNo": serializers.IntegerField(default=1),
            "pageSize": serializers.IntegerField(default=10),
            "totalPage": serializers.IntegerField(default=1),
            "totalCount": serializers.IntegerField(default=1),
            "lastId": serializers.CharField(allow_null=True, default=None),
        }

        return inline_serializer(
            name=name,
            fields={
                "data": serializer,
                "pagination": inline_serializer(
                    name=f"Pag{name}",
                    fields=pagination_fields
                ),
                "messagesList": serializers.ListField(child=serializers.CharField(), default=[])
            }
        )
