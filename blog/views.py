from django.core.cache import cache
from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse
from django.shortcuts import redirect


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
        cache.set("health_check", "ok", timeout=1)
        if cache.get("health_check") == "ok":
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
    Custom view to handle 404 Not Found errors.
    Redirects to an external error page for general requests,
    but returns a standardized JSON response for API requests.

    FA:
    نمای سفارشی برای مدیریت خطاهای ۴۰۴.
    تغییر مسیر به یک صفحه خطای خارجی برای درخواست‌های عمومی،
    اما بازگرداندن یک پاسخ JSON استاندارد برای درخواست‌های API.
    """
    if request.path.startswith("/api/"):
        return JsonResponse(
            {
                "data": None,
                "messagesList": ["The requested API endpoint was not found."],
            },
            status=404,
        )
    return redirect("https://atom-game.ir/404.html")
