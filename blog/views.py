from django.db import connections
from django.db.utils import OperationalError
from django.http import HttpResponse, JsonResponse

from common.cache import cache_manager


def robots_txt_view(request):
    """
    EN: Prevent search engines from crawling or indexing the headless CMS API origin directly.
    FA: جلوگیری از خزش و ایندکس مستقیم دامنه بک‌اند headless وبلاگ توسط موتورهای جست‌وجو.
    """
    response = HttpResponse(
        "User-agent: *\nDisallow: /\n",
        content_type="text/plain; charset=utf-8",
    )
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response


def health_check(request):
    """
    EN:
    Enhanced health check endpoint that verifies database and Redis connectivity.
    Returns 200 if both are healthy, 503 otherwise.

    FA:
    اندپوینت ارتقا یافته بررسی سلامت که اتصال پایگاه داده و Redis را تایید می‌کند.
    اگر هر دو سالم باشند کد ۲۰۰ و در غیر این صورت کد ۵۰۳ برمی‌گرداند.
    """
    health_status = {
        "status": "healthy",
        "services": {
            "database": "unknown",
            "redis": "unknown",
        },
    }
    is_healthy = True

    # EN: Check Database connectivity
    # FA: بررسی اتصال پایگاه داده
    try:
        db_conn = connections["default"]
        db_conn.cursor()
        health_status["services"]["database"] = "healthy"
    except OperationalError:
        health_status["services"]["database"] = "unhealthy"
        is_healthy = False
    except Exception as e:
        health_status["services"]["database"] = f"error: {str(e)}"
        is_healthy = False

    # EN: Check Redis (Cache) connectivity
    # FA: بررسی اتصال Redis (کش)
    try:
        cache_manager.set("health_check", "ok", soft_ttl_sec=1, hard_ttl_sec=2)
        if cache_manager.get("health_check") == "ok":
            health_status["services"]["redis"] = "healthy"
        else:
            health_status["services"]["redis"] = "unhealthy"
            is_healthy = False
    except Exception as e:
        health_status["services"]["redis"] = f"error: {str(e)}"
        is_healthy = False

    if not is_healthy:
        health_status["status"] = "unhealthy"
        return JsonResponse(health_status, status=503)

    return JsonResponse(health_status)


def page_not_found_view(request, exception):
    """
    EN:
    Custom view to handle 404 Not Found errors without an external redirect.
    FA:
    نمای سفارشی برای مدیریت خطاهای ۴۰۴ با کد وضعیت ۴۰۴ واقعی و هدر noindex.
    """
    message = (
        "The requested API endpoint was not found."
        if request.path.startswith("/api/")
        else "The requested page was not found."
    )
    response = JsonResponse(
        {
            "data": None,
            "messagesList": [message],
        },
        status=404,
    )
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response
