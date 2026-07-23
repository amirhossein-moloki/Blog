"""
EN: Cache Subsystem entry point. Exports central services and configures wiring.
FA: نقطه ورود زیرسیستم کش. صادر کردن سرویس‌های مرکزی و پیکربندی ارتباطات آن‌ها.
"""

from .manager import CacheManager, cache_manager
from .monitoring import metrics_tracker
from .policies import CacheLevel, build_cache_key, get_ttl_by_level, get_ttl_with_jitter
from .services import PrefetchService, WarmupService, prefetch_service, warmup_service

# EN: Wire services to the central cache manager instance
# FA: متصل کردن سرویس‌ها به نمونه مدیر کش مرکزی
warmup_service.cache_manager = cache_manager
prefetch_service.cache_manager = cache_manager

# EN: Automatically start predictive prefetch background loop on load
# FA: آغاز خودکار حلقه پس‌زمینه پیش‌خوانی پیش‌بینانه در زمان بارگذاری
prefetch_service.start_background_loop()

__all__ = [
    "cache_manager",
    "CacheManager",
    "warmup_service",
    "prefetch_service",
    "WarmupService",
    "PrefetchService",
    "metrics_tracker",
    "build_cache_key",
    "get_ttl_by_level",
    "get_ttl_with_jitter",
    "CacheLevel",
]
