import logging

from django.conf import settings
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler

# Get an instance of a logger
logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF views.
    This function handles standard DRF errors and general Python errors,
    returning a standard JSON response with an English message.
    """
    # Call DRF's default handler to get the initial response
    exception_handler(exc, context)

    # Determine error message details based on the exception type
    if isinstance(exc, NotAuthenticated):
        detail = "Authentication not performed. Please log in to your account first."
        status_code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(exc, PermissionDenied):
        detail = "You do not have the required permissions to perform this operation."
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, NotFound) or isinstance(exc, Http404):
        detail = "The requested entity was not found."
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, APIException):
        # For other DRF errors, the error details themselves are used
        detail = exc.detail
        status_code = exc.status_code
    else:
        # For unforeseen errors (internal server errors)
        # Log the exception with traceback
        logger.error(
            "Internal Server Error: %s",
            str(exc),
            exc_info=True,
            extra={
                "view": context["view"].__class__.__name__,
                "request_path": context["request"].path,
                "request_method": context["request"].method,
            },
        )

        # In DEBUG mode, display error details to aid debugging
        if settings.DEBUG:
            detail = f"Internal server error: {str(exc)}"
        else:
            detail = (
                "An unexpected error occurred on the server. Please try again later."
            )
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    # Prepare messagesList
    messages_list = []
    if isinstance(detail, list):
        messages_list = detail
    elif isinstance(detail, dict):
        # Convert dict details to a list of messages
        for field, errors in detail.items():
            if isinstance(errors, list):
                for error in errors:
                    messages_list.append(f"{field}: {error}")
            else:
                messages_list.append(f"{field}: {errors}")
    else:
        messages_list.append(str(detail))

    custom_response_data = {
        "data": None,
        "pagination": {
            "pageNo": 1,
            "pageSize": 1000,
            "totalPage": 0,
            "totalCount": 0,
            "lastId": None,
        },
        "messagesList": messages_list,
    }

    return Response(custom_response_data, status=status_code)
