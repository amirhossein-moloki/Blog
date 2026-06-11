from django.core.cache import cache
from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse
from django.shortcuts import redirect


def health_check(request):
    """
    Enhanced health check endpoint that verifies database and Redis connectivity.
    """
    health_status = {
        "status": "healthy",
        "services": {
            "database": "unknown",
            "redis": "unknown",
        },
    }
    is_healthy = True

    # Check Database
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

    # Check Redis (Cache)
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
    Redirects all 404 errors to the specified static 404 page.
    """
    return redirect("https://atom-game.ir/404.html")
