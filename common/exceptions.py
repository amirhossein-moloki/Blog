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

# EN: Get an instance of a logger
# FA: دریافت یک نمونه از logger
logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    EN:
    Custom exception handler for DRF views.
    This function handles standard DRF errors and general Python errors,
    returning a standardized JSON response format.

    FA:
    مدیریت‌کننده استثنای سفارشی برای Viewهای DRF.
    این تابع خطاهای استاندارد DRF و خطاهای عمومی پایتون را مدیریت کرده
    و یک پاسخ JSON با ساختار استاندارد بازمی‌گرداند.
    """
    # EN: Call DRF's default handler to get the initial response
    # FA: فراخوانی هندلر پیش‌فرض DRF برای دریافت پاسخ اولیه
    exception_handler(exc, context)

    # EN: Determine error message details based on the exception type
    # FA: تعیین جزئیات پیام خطا بر اساس نوع استثنا
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
        # EN: For other DRF errors, the error details themselves are used
        # FA: برای سایر خطاهای DRF، از جزئیات خود خطا استفاده می‌شود
        detail = exc.detail
        status_code = exc.status_code
    else:
        # EN: For unforeseen errors (internal server errors)
        # FA: برای خطاهای پیش‌بینی نشده (خطاهای داخلی سرور)
        # EN: Log the exception with traceback
        # FA: ثبت استثنا به همراه traceback در لاگ
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

        # EN: In DEBUG mode, display error details to aid debugging
        # FA: در حالت DEBUG، جزئیات خطا برای کمک به دیباگ نمایش داده می‌شود
        if settings.DEBUG:
            detail = f"Internal server error: {str(exc)}"
        else:
            detail = (
                "An unexpected error occurred on the server. Please try again later."
            )
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    # EN: Prepare messagesList by converting different detail formats to a list of strings
    # FA: آماده‌سازی messagesList با تبدیل فرمت‌های مختلف جزئیات به لیستی از رشته‌ها
    messages_list = []
    if isinstance(detail, list):
        messages_list = detail
    elif isinstance(detail, dict):
        # EN: Convert dict details to a list of messages
        # FA: تبدیل جزئیات دیکشنری به لیستی از پیام‌ها
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
        "messagesList": messages_list,
    }

    return Response(custom_response_data, status=status_code)
