"""
EN: Local cache performance metrics tracker and Redis server telemetry integration.
FA: ردیاب محلی متریک‌های عملکرد کش و یکپارچگی تله‌متری سرور Redis.
"""

import logging
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class MetricsTracker:
    """
    EN: High-performance, thread-safe cache metrics collector and reporter.
    FA: جمع‌آوری‌کننده و گزارش‌دهنده متریک‌های کش با کارایی بالا و ایمن برای استفاده چندنخی.
    """

    def __init__(self) -> None:
        self._hits = 0
        self._misses = 0
        self._lookups_count = 0
        self._total_lookup_time = 0.0
        self._total_rebuild_time = 0.0
        self._rebuilds_count = 0
        self._warmup_duration = 0.0
        self._commands_count = 0
        self._top_missed_keys: Dict[str, int] = {}
        self._warmup_queued = 0
        self._warmup_success = 0
        self._warmup_failure = 0
        self._total_celery_execution_time = 0.0
        self._celery_execution_count = 0
        self._lock = threading.Lock()

    def record_hit(self, lookup_time_ms: float) -> None:
        """
        EN: Records a cache hit and its lookup duration in milliseconds.
        FA: ثبت یک برخورد کش (Hit) و زمان جستجوی آن به میلی‌ثانیه.
        """
        with self._lock:
            self._hits += 1
            self._lookups_count += 1
            self._total_lookup_time += lookup_time_ms
            self._commands_count += 1

    def record_miss(self, lookup_time_ms: float, key: str) -> None:
        """
        EN: Records a cache miss and its lookup duration in milliseconds.
        FA: ثبت یک عدم برخورد کش (Miss) و زمان جستجوی آن به میلی‌ثانیه به همراه کلید مربوطه.
        """
        with self._lock:
            self._misses += 1
            self._lookups_count += 1
            self._total_lookup_time += lookup_time_ms
            self._commands_count += 1
            self._top_missed_keys[key] = self._top_missed_keys.get(key, 0) + 1

    def record_rebuild(self, rebuild_time_ms: float) -> None:
        """
        EN: Records a cache rebuild duration.
        FA: ثبت زمان بازسازی داده‌های کش.
        """
        with self._lock:
            self._rebuilds_count += 1
            self._total_rebuild_time += rebuild_time_ms

    def record_warmup(self, duration_sec: float) -> None:
        """
        EN: Records warmup operation duration.
        FA: ثبت زمان عملیات پیش‌گرم کردن کش.
        """
        with self._lock:
            self._warmup_duration = duration_sec

    def record_warmup_queued(self) -> None:
        """
        EN: Records a warmup task being queued.
        FA: ثبت صف‌بندی شدن تسک پیش‌گرم کردن کش.
        """
        with self._lock:
            self._warmup_queued += 1

    def record_warmup_success(self, duration_sec: float) -> None:
        """
        EN: Records a successful warmup task execution.
        FA: ثبت موفقیت‌آمیز بودن تسک پیش‌گرم کردن کش.
        """
        with self._lock:
            self._warmup_success += 1
            self._warmup_duration = duration_sec

    def record_warmup_failure(self) -> None:
        """
        EN: Records a failed warmup task execution.
        FA: ثبت خطای تسک پیش‌گرم کردن کش.
        """
        with self._lock:
            self._warmup_failure += 1

    def record_celery_execution(self, duration_sec: float) -> None:
        """
        EN: Records the Celery task execution duration.
        FA: ثبت زمان اجرای تسک Celery.
        """
        with self._lock:
            self._celery_execution_count += 1
            self._total_celery_execution_time += duration_sec

    def record_command(self) -> None:
        """
        EN: Increments general Redis/cache operation counter.
        FA: افزایش شمارنده کل دستورات فرستاده شده به کش.
        """
        with self._lock:
            self._commands_count += 1

    def get_local_metrics(self) -> Dict[str, Any]:
        """
        EN: Returns the accumulated thread-safe local cache statistics.
        FA: آمار تجمیع‌شده محلی کش را به صورت ایمن بازمی‌گرداند.
        """
        with self._lock:
            total = self._hits + self._misses
            hit_ratio = (self._hits / total) if total > 0 else 0.0
            avg_lookup = (
                (self._total_lookup_time / self._lookups_count)
                if self._lookups_count > 0
                else 0.0
            )
            avg_rebuild = (
                (self._total_rebuild_time / self._rebuilds_count)
                if self._rebuilds_count > 0
                else 0.0
            )

            # EN: Sort top missed keys
            # FA: مرتب‌سازی کلیدهایی که بیشترین خطا (Miss) را داشته‌اند
            sorted_missed = sorted(
                self._top_missed_keys.items(), key=lambda x: x[1], reverse=True
            )[:10]

            avg_celery = (
                (self._total_celery_execution_time / self._celery_execution_count)
                if self._celery_execution_count > 0
                else 0.0
            )

            return {
                "hits_count": self._hits,
                "misses_count": self._misses,
                "hit_ratio": round(hit_ratio, 4),
                "hit_rate_percentage": round(hit_ratio * 100, 2),
                "miss_rate_percentage": (
                    round((1 - hit_ratio) * 100, 2) if total > 0 else 0.0
                ),
                "average_lookup_time_ms": round(avg_lookup, 4),
                "average_rebuild_time_ms": round(avg_rebuild, 4),
                "warmup_duration_sec": round(self._warmup_duration, 4),
                "warmup_queued_count": self._warmup_queued,
                "warmup_success_count": self._warmup_success,
                "warmup_failure_count": self._warmup_failure,
                "average_celery_execution_time_sec": round(avg_celery, 4),
                "commands_count": self._commands_count,
                "top_missed_keys": dict(sorted_missed),
            }

    def get_redis_telemetry(
        self, redis_client: Optional[Any]
    ) -> Dict[str, Any]:  # pragma: no cover
        """
        EN: Connects directly to Redis client and extracts raw performance and memory telemetry.
        FA: اتصال مستقیم به کلاینت Redis و استخراج تله‌متری خام عملکرد و حافظه مصرفی.
        """
        if not redis_client:
            return {
                "redis_available": False,
                "status_message": "Redis client is offline or disabled",
            }

        try:
            info = redis_client.info()
            # EN: Get DB key count (usually DB 1 is used for cache as per settings)
            # FA: دریافت تعداد کلیدها در دیتابیس فعال
            db_keys = 0
            for k in info.keys():
                if k.startswith("db"):
                    db_keys += info[k].get("keys", 0)

            return {
                "redis_available": True,
                "used_memory_bytes": int(info.get("used_memory", 0)),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "used_cpu_sys": float(info.get("used_cpu_sys", 0.0)),
                "used_cpu_user": float(info.get("used_cpu_user", 0.0)),
                "keys_count": db_keys,
                "expired_keys": int(info.get("expired_keys", 0)),
                "evictions": int(info.get("evicted_keys", 0)),
                "fragmentation_ratio": float(info.get("mem_fragmentation_ratio", 0.0)),
                "commands_processed_per_second": int(
                    info.get("instantaneous_ops_per_sec", 0)
                ),
                "connected_clients": int(info.get("connected_clients", 0)),
            }
        except Exception as e:
            logger.warning(f"Failed to fetch Redis telemetry metrics: {e}")
            return {
                "redis_available": False,
                "status_message": f"Telemetry retrieval failed: {str(e)}",
            }


# EN: Global Metrics Tracker instance
# FA: نمونه متریک ردیاب سراسری
metrics_tracker = MetricsTracker()
