"""
EN: Cache policies, TTL configurations, TTL jittering, and canonical cache key builder.
FA: سیاست‌های کش، تنظیمات TTL، افزودن جیتر به TTL و سازنده کلید کش استاندارد.
"""

import hashlib
import random
from typing import Any, Dict, Optional

# EN: Cache Levels and TTL defaults (in seconds)
# FA: سطوح کش و مقادیر پیش‌فرض TTL (به ثانیه)
CACHE_TTL_SHORT = 300  # EN: 5 minutes (Short Cache: Level 2)
CACHE_TTL_MEDIUM = 14400  # EN: 4 hours (Medium Cache: Level 3)
CACHE_TTL_LONG = 1209600  # EN: 14 days (Long Cache: Level 4)


class CacheLevel:
    """
    EN: Defines caching level configurations.
    FA: تنظیمات سطوح کش را تعریف می‌کند.
    """

    LEVEL_1 = "no_cache"
    LEVEL_2 = "short"
    LEVEL_3 = "medium"
    LEVEL_4 = "long"


def get_ttl_with_jitter(base_ttl: int, jitter_percentage: float = 0.1) -> int:
    """
    EN: Adds random jitter to the TTL to prevent Cache Avalanche.
    FA: برای جلوگیری از بهمن کش (Cache Avalanche) جیتر تصادفی به TTL اضافه می‌کند.
    """
    if base_ttl <= 0:
        return base_ttl
    jitter_range = int(base_ttl * jitter_percentage)
    if jitter_range <= 0:
        return base_ttl
    return base_ttl + random.randint(-jitter_range, jitter_range)


def get_ttl_by_level(level: str) -> int:
    """
    EN: Returns the TTL (seconds) for a given cache level.
    FA: مقدار TTL (ثانیه) را برای یک سطح کش داده‌شده بازمی‌گرداند.
    """
    if level == CacheLevel.LEVEL_2:
        return get_ttl_with_jitter(CACHE_TTL_SHORT)
    elif level == CacheLevel.LEVEL_3:
        return get_ttl_with_jitter(CACHE_TTL_MEDIUM)
    elif level == CacheLevel.LEVEL_4:
        return get_ttl_with_jitter(CACHE_TTL_LONG)
    return 0


def build_cache_key(
    module: str,
    resource: str,
    identifier: str,
    params: Optional[Dict[str, Any]] = None,
    api_version: str = "v1",
    tenant: str = "default",
    lang: str = "en",
    timezone: str = "UTC",
) -> str:
    """
    EN:
    Generates a canonical cache key matching the required format:
    project:<api_version>:<module>:<resource>:<identifier>:<hash>

    Normalizes and sorts query parameters to avoid duplicate cache entries.

    FA:
    یک کلید کش استاندارد مطابق با فرمت درخواستی تولید می‌کند:
    project:<api_version>:<module>:<resource>:<identifier>:<hash>

    پارامترهای کوئری را مرتب و نرمال می‌کند تا از ایجاد ورودی‌های تکراری کش جلوگیری شود.
    """
    # EN: Normalize and clean parameters
    # FA: نرمال‌سازی و پاک‌سازی پارامترها
    normalized_parts = []
    if params:
        # EN: Sort keys to ensure stability
        # FA: مرتب‌سازی کلیدها برای تضمین پایداری
        sorted_keys = sorted(params.keys())
        for key in sorted_keys:
            val = params[key]
            if val is not None:
                # EN: Avoid useless/empty parameters
                # FA: نادیده گرفتن پارامترهای بی‌فایده/خالی
                normalized_parts.append(f"{key}={str(val).strip().lower()}")

    # EN: Append standard context parameters
    # FA: افزودن پارامترهای استاندارد کانتکست
    normalized_parts.append(f"lang={lang.strip().lower()}")
    normalized_parts.append(f"tenant={tenant.strip().lower()}")
    normalized_parts.append(f"tz={timezone.strip().lower()}")

    param_str = "&".join(normalized_parts)
    param_hash = hashlib.md5(param_str.encode("utf-8")).hexdigest()[:12]

    # EN: Construct canonical cache key
    # FA: ساخت کلید کش استاندارد
    return f"project:{api_version}:{module}:{resource}:{identifier}:{param_hash}"
