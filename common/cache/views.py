"""
EN: Health check views for Cache, Redis, and Cache-Manager with performance telemetry.
FA: نماهای بررسی سلامت برای کش، ردیس و مدیریت کش به همراه تله‌متری عملکردی سیستم.
"""

import logging
import time

from django.core.cache import caches
from django.http import JsonResponse
from django.views import View

from .manager import cache_manager
from .monitoring import metrics_tracker

logger = logging.getLogger(__name__)


class CacheHealthView(View):
    """
    EN: Validates general Django cache connectivity and operations.
    FA: صحت ارتباط و کارکرد پایه سیستم کش جنگو را بررسی می‌کند.
    """

    def get(self, request, *args, **kwargs) -> JsonResponse:
        start_time = time.time()
        try:
            django_cache = caches["default"]
            test_key = "project:v1:health:cache_test"
            test_val = "healthy_status"

            # EN: Test write
            # FA: تست نوشتن
            django_cache.set(test_key, test_val, timeout=5)

            # EN: Test read
            # FA: تست خواندن
            read_val = django_cache.get(test_key)

            # EN: Test delete
            # FA: تست حذف
            django_cache.delete(test_key)

            duration = (time.time() - start_time) * 1000.0

            if read_val == test_val:
                return JsonResponse(
                    {
                        "status": "healthy",
                        "timestamp": time.time(),
                        "duration_ms": round(duration, 2),
                        "backend": django_cache.__class__.__name__,
                    },
                    status=200,
                )

            raise ValueError("Value mismatch during health-check read-write loop")
        except Exception as e:
            logger.error(f"Cache Health Check Failed: {e}", exc_info=True)
            return JsonResponse(
                {"status": "unhealthy", "timestamp": time.time(), "error": str(e)},
                status=503,
            )


class RedisHealthView(View):
    """
    EN: Validates direct Redis server connectivity and raw operational status.
    FA: صحت ارتباط مستقیم با سرور Redis و وضعیت کارکرد آن را بررسی می‌کند.
    """

    def get(self, request, *args, **kwargs) -> JsonResponse:
        start_time = time.time()
        try:
            client = cache_manager._get_raw_client()
            if not client:
                return JsonResponse(
                    {
                        "status": "unhealthy",
                        "timestamp": time.time(),
                        "message": "Redis is disabled or client is offline",
                    },
                    status=503,
                )

            # EN: Ping Redis
            # FA: ارسال پینگ به ردیس
            client.ping()
            duration = (time.time() - start_time) * 1000.0

            # EN: Fetch redis telemetry info
            # FA: دریافت اطلاعات تله‌متری ردیس
            telemetry = metrics_tracker.get_redis_telemetry(client)

            return JsonResponse(
                {
                    "status": "healthy",
                    "timestamp": time.time(),
                    "duration_ms": round(duration, 2),
                    "telemetry": telemetry,
                },
                status=200,
            )
        except Exception as e:
            logger.error(f"Redis Health Check Failed: {e}", exc_info=True)
            return JsonResponse(
                {"status": "unhealthy", "timestamp": time.time(), "error": str(e)},
                status=503,
            )


class CacheManagerHealthView(View):
    """
    EN: Validates Cache Manager serialization, compression, locking, and exports telemetry metrics.
    FA: صحت عملکرد سریالایز، فشرده‌سازی، قفل همزمانی و خروجی متریک‌های عملکردی مدیر کش را ارزیابی می‌کند.
    """

    def get(self, request, *args, **kwargs) -> JsonResponse:
        start_time = time.time()
        try:
            # EN: 1. Test standard cache manager write/read loop
            # FA: ۱. تست چرخه نوشتن و خواندن استاندارد در مدیر کش
            test_key = "project:v1:health:manager_test"
            test_data = {"test_uuid_val": "abc-123", "nested": [1, 2, 3]}

            cache_manager.set(test_key, test_data, soft_ttl_sec=5, hard_ttl_sec=10)
            read_data = cache_manager.get(test_key)
            cache_manager.delete(test_key)

            if read_data != test_data:
                raise ValueError("Data mismatch in CacheManager read-write cycle")

            # EN: 2. Test locking
            # FA: ۲. تست قفل همزمانی
            lock_key = "health:lock_test"
            success, token = cache_manager.try_acquire_lock(
                lock_key, expire_sec=5, timeout_sec=1
            )
            if not success or not token:
                raise ValueError("Failed to acquire test lock")

            released = cache_manager.release_lock(lock_key, token)
            if not released:
                raise ValueError("Failed to release test lock")

            duration = (time.time() - start_time) * 1000.0

            # EN: 3. Retrieve global metrics and telemetries
            # FA: ۳. دریافت کل متریک‌ها و تله‌متری‌های عملکردی سراسری
            local_metrics = metrics_tracker.get_local_metrics()
            client = cache_manager._get_raw_client()
            redis_telemetry = metrics_tracker.get_redis_telemetry(client)

            return JsonResponse(
                {
                    "status": "healthy",
                    "timestamp": time.time(),
                    "duration_ms": round(duration, 2),
                    "serializer": cache_manager.serializer.__class__.__name__,
                    "compressor": cache_manager.compressor.__class__.__name__,
                    "metrics": {"local": local_metrics, "redis": redis_telemetry},
                },
                status=200,
            )
        except Exception as e:
            logger.error(f"Cache Manager Health Check Failed: {e}", exc_info=True)
            return JsonResponse(
                {"status": "unhealthy", "timestamp": time.time(), "error": str(e)},
                status=503,
            )
