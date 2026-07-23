"""
EN: Central Cache Manager service. Implements Cache-Aside, Stale-While-Revalidate, size limits, and fallbacks.
FA: سرویس مرکزی مدیریت کش. پیاده‌سازی الگوهای Cache-Aside و Stale-While-Revalidate، محدودیت‌های حجم داده و سوئیچ اضطراری.
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import threading
from concurrent.futures import ThreadPoolExecutor

from django.core.cache import caches
from django.conf import settings

from .compressors import BaseCacheCompressor, GzipCompressor, ZstdCompressor
from .invalidation import InvalidationManager
from .locks import DistributedLock
from .monitoring import metrics_tracker
from .policies import build_cache_key, get_ttl_by_level, get_ttl_with_jitter, CACHE_TTL_MEDIUM
from .serializers import BaseCacheSerializer, JSONSerializer, MessagePackSerializer

logger = logging.getLogger(__name__)


class CacheManager:
    """
    EN:
    Enterprise-grade Central Cache Manager.
    Encapsulates all cache actions, ensuring SOLID principles, thread safety, and fail-safe fallbacks.

    FA:
    مدیر کش مرکزی در سطح سازمانی.
    تمامی فعالیت‌های کش را کپسوله‌سازی می‌کند و اصول SOLID، ایمنی نخ‌ها و بازیابی اضطراری در زمان قطع اتصال را تضمین می‌کند.
    """

    def __init__(
        self,
        serializer: Optional[BaseCacheSerializer] = None,
        compressor: Optional[BaseCacheCompressor] = None,
        compression_threshold_bytes: int = 2048,
        max_object_size_bytes: int = 5242880,  # EN: 5MB limit
    ) -> None:
        """
        EN: Initializes the Cache Manager with default serialization, compression, and thresholds.
        FA: مقداردهی اولیه مدیریت کش با سریالایزر، فشرده‌ساز و آستانه‌های پیش‌فرض.
        """
        self.serializer = serializer or MessagePackSerializer()
        self.compressor = compressor or ZstdCompressor()
        self.compression_threshold_bytes = compression_threshold_bytes
        self.max_object_size_bytes = max_object_size_bytes

        # EN: Thread pool for background non-blocking revalidation (Stale-While-Revalidate)
        # FA: استخر نخ‌ها برای اجرای پس‌زمینه و غیرمسدودکننده بازسازی کش (Stale-While-Revalidate)
        self._executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="cache-revalidate")

        # EN: Setup underlying Django Cache connection
        # FA: راه‌اندازی اتصال به موتور کش جنگو
        self._django_cache = caches["default"]
        self._redis_client = None
        self._is_redis_available = False

        # EN: Setup Invalidation Manager
        # FA: راه‌اندازی مدیریت ابطال کش
        self.invalidation = InvalidationManager(self._django_cache)

        # EN: Detect raw redis client for advanced locks or metrics if possible
        # FA: تشخیص کلاینت خام ردیس برای قفل‌های پیشرفته یا متریک‌ها در صورت امکان
        self._detect_redis()

    def _detect_redis(self) -> None:
        """
        EN: Safely attempts to detect and keep reference to raw Redis client.
        FA: تلاش ایمن برای تشخیص کلاینت خام Redis.
        """
        try:
            if hasattr(self._django_cache, "client") and hasattr(self._django_cache.client, "get_client"):
                # EN: django-redis client
                # FA: کلاینت مخصوص django-redis
                self._redis_client = self._django_cache.client.get_client()
                # EN: Test ping to verify operational status
                # FA: ارسال پینگ برای تایید در دسترس بودن سرویس
                self._redis_client.ping()
                self._is_redis_available = True
        except Exception as e:
            logger.warning(f"Redis not available or not configured: {e}. Falling back to Django cache backend.")
            self._redis_client = None
            self._is_redis_available = False

    def _get_raw_client(self) -> Optional[Any]:
        """
        EN: Returns the active Redis client, checking ping to maintain fail-safe state.
        FA: کلاینت فعال Redis را با ارسال پینگ بررسی کرده و برمی‌گرداند.
        """
        if not self._is_redis_available or self._redis_client is None:
            return None
        try:
            self._redis_client.ping()
            return self._redis_client
        except Exception:
            logger.warning("Redis ping failed. Disabling raw Redis interactions.")
            self._is_redis_available = False
            return None

    # --- CORE SYNC/ASYNC API IMPLEMENTATION ---

    def _pack_envelope(
        self,
        data: Any,
        group: Optional[str] = None,
        tags: Optional[List[str]] = None,
        soft_ttl_sec: Optional[int] = None,
        hard_ttl_sec: Optional[int] = None
    ) -> Optional[bytes]:
        """
        EN: Serializes, compresses, and wraps cache object in an envelope with metadata.
        FA: سریالایز، فشرده‌سازی و بسته‌بندی شیء کش در یک پاکت حاوی متادیتا.
        """
        try:
            serialized = self.serializer.serialize(data)
            serialized_len = len(serialized)

            if serialized_len > self.max_object_size_bytes:
                logger.warning(f"Payload size {serialized_len} exceeds cache limit {self.max_object_size_bytes}. Rejecting.")
                return None

            compressed = False
            payload = serialized
            if serialized_len > self.compression_threshold_bytes:
                payload = self.compressor.compress(serialized)
                compressed = True

            # EN: Build tag-version mappings
            # FA: ساخت مپینگ تگ-نسخه
            tag_versions = {}
            if tags:
                for tag in tags:
                    tag_versions[tag] = self.invalidation.get_tag_version(tag)

            # EN: Build group-version mapping
            # FA: ساخت مپینگ گروه-نسخه
            group_version = self.invalidation.get_version(group) if group else 1

            now = time.time()
            envelope = {
                "p": payload,  # EN: payload bytes
                "c": compressed,
                "g": group,
                "gv": group_version,
                "t": tags or [],
                "tv": tag_versions,
                "st": now + (soft_ttl_sec or 300),
                "ht": now + (hard_ttl_sec or 600)
            }

            # EN: Serialize the entire envelope with JSON
            # FA: سریالایز کردن کل پاکت به فرمت JSON
            # We use local helper to encode byte strings as hex to preserve data in nested JSON structure safely
            if isinstance(envelope["p"], bytes):
                envelope["p"] = envelope["p"].hex()
                envelope["hex_encoded"] = True

            return self.serializer.serialize(envelope)
        except Exception as e:
            logger.error(f"Error packing envelope: {e}", exc_info=True)
            return None

    def _unpack_envelope(self, envelope_bytes: bytes) -> Tuple[Optional[Any], bool]:
        """
        EN: Unpacks, verifies versions/tags, decompresses, and returns data and stale flag.
        FA: باز کردن پاکت کش، بررسی نسخه‌ها/تگ‌ها، باز کردن فشرده‌سازی و بازگرداندن داده و فلگ کهنگی (stale).
        """
        if not envelope_bytes:
            return None, False

        try:
            envelope = self.serializer.deserialize(envelope_bytes)
            if not isinstance(envelope, dict):
                return None, False

            # EN: Check group version validity
            # FA: بررسی اعتبار نسخه گروه
            group = envelope.get("g")
            if group:
                current_group_ver = self.invalidation.get_version(group)
                if envelope.get("gv", 1) < current_group_ver:
                    logger.debug(f"Cache stale: group '{group}' version changed from {envelope.get('gv')} to {current_group_ver}")
                    return None, False

            # EN: Check tag versions validity
            # FA: بررسی اعتبار نسخه‌های تگ‌ها
            tag_versions = envelope.get("tv", {})
            for tag, stored_ver in tag_versions.items():
                current_tag_ver = self.invalidation.get_tag_version(tag)
                if stored_ver < current_tag_ver:
                    logger.debug(f"Cache stale: tag '{tag}' version changed from {stored_ver} to {current_tag_ver}")
                    return None, False

            # EN: Check expiration times
            # FA: بررسی زمان‌های انقضا
            now = time.time()
            hard_expire = envelope.get("ht", 0)
            soft_expire = envelope.get("st", 0)

            if now > hard_expire:
                # EN: Hard-expired
                # FA: انقضای سخت اتفاق افتاده است
                return None, False

            is_stale = now > soft_expire

            # EN: Extract payload
            # FA: استخراج داده اصلی
            payload = envelope.get("p")
            if envelope.get("hex_encoded", False) and isinstance(payload, str):
                payload = bytes.fromhex(payload)

            if envelope.get("c", False):
                payload = self.compressor.decompress(payload)

            data = self.serializer.deserialize(payload)
            return data, is_stale

        except Exception as e:
            logger.error(f"Error unpacking cache envelope: {e}", exc_info=True)
            return None, False

    # --- MAIN API INTERFACES (Thread-safe, Fail-safe) ---

    def get(self, key: str) -> Optional[Any]:
        """
        EN: Synchronous retrieval.
        FA: دریافت همزمان داده از کش.
        """
        start_time = time.time()
        try:
            raw_data = self._django_cache.get(key)
            duration_ms = (time.time() - start_time) * 1000.0

            if raw_data is None:
                metrics_tracker.record_miss(duration_ms, key)
                return None

            data, is_stale = self._unpack_envelope(raw_data)
            if data is None:
                metrics_tracker.record_miss(duration_ms, key)
                return None

            metrics_tracker.record_hit(duration_ms)
            return data
        except Exception as e:
            logger.error(f"Error in cache get: {e}. Graceful fallback to None.")
            duration_ms = (time.time() - start_time) * 1000.0
            metrics_tracker.record_miss(duration_ms, key)
            return None

    async def get_async(self, key: str) -> Optional[Any]:
        """
        EN: Asynchronous retrieval (Async-first API).
        FA: دریافت ناهمزمان داده از کش.
        """
        # EN: Wrap standard sync in coroutine cleanly
        # FA: اجرای متد همزمان به صورت ایمن در قالب کوروتین
        return self.get(key)

    async def GetAsync(self, key: str) -> Optional[Any]:
        """EN: CamelCase alias for GetAsync. FA: نام مستعار GetAsync."""
        return await self.get_async(key)

    def set(
        self,
        key: str,
        value: Any,
        group: Optional[str] = None,
        tags: Optional[List[str]] = None,
        soft_ttl_sec: Optional[int] = None,
        hard_ttl_sec: Optional[int] = None
    ) -> bool:
        """
        EN: Synchronous set operation.
        FA: ثبت داده به همراه متادیتا در کش به صورت همزمان.
        """
        if value is None:
            return False

        # EN: Generate random jitter on hard TTL
        # FA: تولید جیتر تصادفی برای انقضای سخت
        hard_ttl_sec = hard_ttl_sec or CACHE_TTL_MEDIUM
        soft_ttl_sec = soft_ttl_sec or int(hard_ttl_sec * 0.7)  # EN: default soft TTL to 70% of hard TTL

        hard_ttl_jittered = get_ttl_with_jitter(hard_ttl_sec)

        envelope = self._pack_envelope(
            data=value,
            group=group,
            tags=tags,
            soft_ttl_sec=soft_ttl_sec,
            hard_ttl_sec=hard_ttl_jittered
        )
        if envelope is None:
            return False

        try:
            self._django_cache.set(key, envelope, timeout=hard_ttl_jittered)
            metrics_tracker.record_command()
            return True
        except Exception as e:
            logger.error(f"Error in cache set: {e}. PostgreSQL remains the single source of truth.")
            return False

    async def set_async(
        self,
        key: str,
        value: Any,
        group: Optional[str] = None,
        tags: Optional[List[str]] = None,
        soft_ttl_sec: Optional[int] = None,
        hard_ttl_sec: Optional[int] = None
    ) -> bool:
        """
        EN: Asynchronous set operation.
        FA: ثبت داده به همراه متادیتا در کش به صورت ناهمزمان.
        """
        return self.set(key, value, group, tags, soft_ttl_sec, hard_ttl_sec)

    async def SetAsync(
        self,
        key: str,
        value: Any,
        group: Optional[str] = None,
        tags: Optional[List[str]] = None,
        soft_ttl_sec: Optional[int] = None,
        hard_ttl_sec: Optional[int] = None
    ) -> bool:
        """EN: CamelCase alias for SetAsync. FA: نام مستعار SetAsync."""
        return await self.set_async(key, value, group, tags, soft_ttl_sec, hard_ttl_sec)

    def delete(self, key: str) -> bool:
        """
        EN: Synchronous delete operation.
        FA: حذف همزمان کلید از کش.
        """
        try:
            self._django_cache.delete(key)
            metrics_tracker.record_command()
            return True
        except Exception as e:
            logger.error(f"Error deleting key {key}: {e}")
            return False

    async def remove_async(self, key: str) -> bool:
        """
        EN: Asynchronous remove operation.
        FA: حذف ناهمزمان کلید از کش.
        """
        return self.delete(key)

    async def RemoveAsync(self, key: str) -> bool:
        """EN: CamelCase alias for RemoveAsync. FA: نام مستعار RemoveAsync."""
        return await self.remove_async(key)

    def remove_by_version(self, group: str) -> bool:
        """
        EN: Version based invalidation (Increment version, old keys naturally expire).
        FA: ابطال بر اساس نسخه (افزایش نسخه گروه، در نتیجه کلیدهای قدیمی خودبه‌خود منقضی می‌شوند).
        """
        try:
            self.invalidation.increment_version(group)
            return True
        except Exception as e:
            logger.error(f"Error removing by version for {group}: {e}")
            return False

    async def RemoveByVersion(self, group: str) -> bool:
        """EN: CamelCase alias for RemoveByVersion. FA: نام مستعار RemoveByVersion."""
        return self.remove_by_version(group)

    def exists(self, key: str) -> bool:
        """
        EN: Checks if a key exists in cache.
        FA: بررسی وجود کلید در کش.
        """
        try:
            return key in self._django_cache
        except Exception:
            return False

    async def exists_async(self, key: str) -> bool:
        """EN: Asynchronous exists. FA: بررسی ناهمزمان وجود کلید."""
        return self.exists(key)

    async def ExistsAsync(self, key: str) -> bool:
        """EN: CamelCase alias for ExistsAsync. FA: نام مستعار ExistsAsync."""
        return await self.exists_async(key)

    def get_or_create(
        self,
        key: str,
        rebuild_callback: Callable[[], Any],
        group: Optional[str] = None,
        tags: Optional[List[str]] = None,
        soft_ttl_sec: Optional[int] = None,
        hard_ttl_sec: Optional[int] = None
    ) -> Any:
        """
        EN:
        Implements Cache Aside Pattern with Stale-While-Revalidate and Distributed Locking.
        On miss: Only one request rebuilds, others wait or get stale.
        On soft-expiry: Serves stale content immediately and triggers non-blocking background revalidation.

        FA:
        الگوی Cache Aside به همراه قابلیت Stale-While-Revalidate و قفل توزیع‌شده.
        در زمان عدم وجود کلید: فقط یک درخواست کش را بازسازی می‌کند، بقیه منتظر می‌مانند یا داده کهنه می‌گیرند.
        در زمان انقضای نرم: داده کهنه بلافاصله بازگردانده شده و بازسازی غیرمسدودکننده در پس‌زمینه آغاز می‌شود.
        """
        start_time = time.time()
        try:
            raw_data = self._django_cache.get(key)
        except Exception as e:
            logger.error(f"Cache engine error during get_or_create: {e}. PostgreSQL fallback.")
            raw_data = None

        if raw_data is not None:
            data, is_stale = self._unpack_envelope(raw_data)
            if data is not None:
                duration_ms = (time.time() - start_time) * 1000.0
                metrics_tracker.record_hit(duration_ms)

                if is_stale:
                    # EN: Trigger background non-blocking revalidation
                    # FA: آغاز فرآیند غیرمسدودکننده پس‌زمینه برای بازسازی کش
                    logger.debug(f"Soft expiry triggered for {key}. Revalidating in background.")
                    self._trigger_background_rebuild(key, rebuild_callback, group, tags, soft_ttl_sec, hard_ttl_sec)

                return data

        # EN: Cache Miss - Rebuild under lock (Stampede protection)
        # FA: عدم برخورد کش - بازسازی داده با استفاده از قفل امنیتی (جلوگیری از یورش به کش)
        duration_ms = (time.time() - start_time) * 1000.0
        metrics_tracker.record_miss(duration_ms, key)

        # EN: Try to acquire Lock to rebuild
        # FA: تلاش برای دریافت قفل جهت بازسازی داده‌ها
        lock = DistributedLock(self._get_raw_client(), key)
        if lock.acquire(expire_sec=15, timeout_sec=2):
            try:
                # EN: Double-check if another request rebuilt it while we waited
                # FA: بررسی مجدد وجود داده، شاید درخواست دیگری در طول انتظار ما آن را ساخته باشد
                try:
                    double_check = self._django_cache.get(key)
                except Exception:
                    double_check = None

                if double_check is not None:
                    data, _ = self._unpack_envelope(double_check)
                    if data is not None:
                        return data

                # EN: Rebuild
                # FA: بازسازی داده‌ها
                rebuild_start = time.time()
                new_value = rebuild_callback()
                rebuild_duration = (time.time() - rebuild_start) * 1000.0
                metrics_tracker.record_rebuild(rebuild_duration)

                # EN: Store in Cache
                # FA: ثبت داده جدید در کش
                self.set(key, new_value, group, tags, soft_ttl_sec, hard_ttl_sec)
                return new_value
            finally:
                lock.release()
        else:
            # EN: Lock timed out, fallback directly to DB query to prevent blocking request
            # FA: خطای انقضای زمان دریافت قفل، اجرای مستقیم کوئری پایگاه داده برای جلوگیری از فریز شدن کلاینت
            logger.warning(f"Cache lock timeout for {key}. Falling back directly to Single Source of Truth.")
            return rebuild_callback()

    async def get_or_create_async(
        self,
        key: str,
        rebuild_callback: Callable[[], Any],
        group: Optional[str] = None,
        tags: Optional[List[str]] = None,
        soft_ttl_sec: Optional[int] = None,
        hard_ttl_sec: Optional[int] = None
    ) -> Any:
        """
        EN: Asynchronous GetOrCreate operation.
        FA: عملیات GetOrCreate ناهمزمان.
        """
        # EN: Django's sync callback can be executed in executor if async context is preferred.
        # FA: کالبک همزمان جنگو را می‌توان در استخر نخ‌ها اجرا کرد در صورتی که کانتکست ناهمزمان ترجیح داده شود.
        return self.get_or_create(key, rebuild_callback, group, tags, soft_ttl_sec, hard_ttl_sec)

    async def GetOrCreateAsync(
        self,
        key: str,
        rebuild_callback: Callable[[], Any],
        group: Optional[str] = None,
        tags: Optional[List[str]] = None,
        soft_ttl_sec: Optional[int] = None,
        hard_ttl_sec: Optional[int] = None
    ) -> Any:
        """EN: CamelCase alias for GetOrCreateAsync. FA: نام مستعار GetOrCreateAsync."""
        return await self.get_or_create_async(key, rebuild_callback, group, tags, soft_ttl_sec, hard_ttl_sec)

    def _trigger_background_rebuild(
        self,
        key: str,
        rebuild_callback: Callable[[], Any],
        group: Optional[str] = None,
        tags: Optional[List[str]] = None,
        soft_ttl_sec: Optional[int] = None,
        hard_ttl_sec: Optional[int] = None
    ) -> None:
        """
        EN: Dispatches the revalidation callback to thread pool.
        FA: ارسال فرآیند بازسازی کش به استخر نخ‌ها به صورت پس‌زمینه.
        """
        def task():
            lock = DistributedLock(self._get_raw_client(), f"rebuild:{key}")
            # EN: Lock with no block to ensure only one thread triggers background revalidation
            # FA: قفل غیرمنتظر شونده برای تضمین اینکه فقط یک نخ بازسازی پس‌زمینه را انجام می‌دهد
            if lock.acquire(expire_sec=10, timeout_sec=0):
                try:
                    logger.info(f"Background revalidating key: {key}")
                    new_value = rebuild_callback()
                    self.set(key, new_value, group, tags, soft_ttl_sec, hard_ttl_sec)
                except Exception as e:
                    logger.error(f"Error in background revalidation task for {key}: {e}", exc_info=True)
                finally:
                    lock.release()

        self._executor.submit(task)

    # --- DISTRIBUTED LOCK IMPLEMENTATION ---

    def try_acquire_lock(self, lock_key: str, expire_sec: int = 10, timeout_sec: int = 5) -> Tuple[bool, Optional[str]]:
        """
        EN: Tries to acquire a lock, returning (success_boolean, token).
        FA: تلاش برای دریافت قفل همزمانی. مقدار برگشتی (success_boolean, token) است.
        """
        lock = DistributedLock(self._get_raw_client(), lock_key)
        success = lock.acquire(expire_sec, timeout_sec)
        return success, lock.token

    async def TryAcquireLock(self, lock_key: str, expire_sec: int = 10, timeout_sec: int = 5) -> Tuple[bool, Optional[str]]:
        """EN: CamelCase alias. FA: نام مستعار."""
        return self.try_acquire_lock(lock_key, expire_sec, timeout_sec)

    def release_lock(self, lock_key: str, token: str) -> bool:
        """
        EN: Releases an acquired lock safely.
        FA: آزادسازی ایمن قفل همزمانی دریافتی.
        """
        lock = DistributedLock(self._get_raw_client(), lock_key)
        lock.token = token
        return lock.release()

    async def ReleaseLock(self, lock_key: str, token: str) -> bool:
        """EN: CamelCase alias. FA: نام مستعار."""
        return self.release_lock(lock_key, token)

    # --- WARMUP / REFRESH INTERFACES ---

    def refresh(self, key: str, rebuild_callback: Callable[[], Any], group: Optional[str] = None, tags: Optional[List[str]] = None, soft_ttl_sec: Optional[int] = None, hard_ttl_sec: Optional[int] = None) -> Any:
        """
        EN: Forces cache rebuild and returns the fresh value.
        FA: اجبار بازسازی کامل کش و ذخیره مقدار تازه.
        """
        new_val = rebuild_callback()
        self.set(key, new_val, group, tags, soft_ttl_sec, hard_ttl_sec)
        return new_val

    async def refresh_async(self, key: str, rebuild_callback: Callable[[], Any], group: Optional[str] = None, tags: Optional[List[str]] = None, soft_ttl_sec: Optional[int] = None, hard_ttl_sec: Optional[int] = None) -> Any:
        """EN: Asynchronous cache refresh. FA: بازسازی کش ناهمزمان."""
        return self.refresh(key, rebuild_callback, group, tags, soft_ttl_sec, hard_ttl_sec)

    async def RefreshAsync(self, key: str, rebuild_callback: Callable[[], Any], group: Optional[str] = None, tags: Optional[List[str]] = None, soft_ttl_sec: Optional[int] = None, hard_ttl_sec: Optional[int] = None) -> Any:
        """EN: CamelCase alias. FA: نام مستعار."""
        return await self.refresh_async(key, rebuild_callback, group, tags, soft_ttl_sec, hard_ttl_sec)

    async def warmup_async(self, key: str, value: Any, group: Optional[str] = None, tags: Optional[List[str]] = None, soft_ttl_sec: Optional[int] = None, hard_ttl_sec: Optional[int] = None) -> bool:
        """
        EN: Warmup caches asynchronously.
        FA: پیش‌گرم کردن کش به صورت ناهمزمان.
        """
        return self.set(key, value, group, tags, soft_ttl_sec, hard_ttl_sec)

    async def WarmupAsync(self, key: str, value: Any, group: Optional[str] = None, tags: Optional[List[str]] = None, soft_ttl_sec: Optional[int] = None, hard_ttl_sec: Optional[int] = None) -> bool:
        """EN: CamelCase alias. FA: نام مستعار."""
        return await self.warmup_async(key, value, group, tags, soft_ttl_sec, hard_ttl_sec)


# EN: Singleton instance of CacheManager
# FA: نمونه سینگلتون CacheManager جهت استفاده متمرکز در سراسر پروژه
cache_manager = CacheManager()
