"""
EN: Distributed and local-fallback thread-safe locking system.
FA: سیستم قفل توزیع‌شده با قابلیت سوئیچ خودکار به قفل محلی ایمن از نظر چندنخی.
"""

import logging
import time
import uuid
from typing import Dict, Optional, Any
import threading

# EN: Get standard logger
# FA: دریافت لاگر استاندارد
logger = logging.getLogger(__name__)


class LocalMemoryLockManager:
    """
    EN: In-memory thread-safe lock manager for fallback operations when Redis is unavailable.
    FA: مدیریت قفل محلی ایمن برای فرآیندهای چندنخی به عنوان جایگزین در زمان عدم دسترسی به Redis.
    """

    def __init__(self) -> None:
        self._locks: Dict[str, threading.Lock] = {}
        self._owner_tokens: Dict[str, str] = {}
        self._expires_at: Dict[str, float] = {}
        self._manager_lock = threading.Lock()

    def try_acquire(self, lock_key: str, expire_sec: int, timeout_sec: int) -> Optional[str]:
        """
        EN: Tries to acquire local lock within timeout. Returns a unique token if successful.
        FA: تلاش برای دریافت قفل محلی در زمان مشخص شده. بازگرداندن توکن منحصربه‌فرد در صورت موفقیت.
        """
        start_time = time.time()
        token = str(uuid.uuid4())

        while True:
            with self._manager_lock:
                current_time = time.time()
                # EN: Cleanup expired locks
                # FA: پاک‌سازی قفل‌های منقضی شده
                if lock_key in self._expires_at and current_time > self._expires_at[lock_key]:
                    self._release_lock_internal(lock_key)

                if lock_key not in self._locks:
                    self._locks[lock_key] = threading.Lock()

                lock = self._locks[lock_key]

            # EN: Attempt to acquire
            # FA: تلاش برای دریافت قفل
            acquired = lock.acquire(blocking=False)
            if acquired:
                with self._manager_lock:
                    self._owner_tokens[lock_key] = token
                    self._expires_at[lock_key] = time.time() + expire_sec
                return token

            if timeout_sec <= 0 or (time.time() - start_time) >= timeout_sec:
                return None

            time.sleep(0.05)

    def release(self, lock_key: str, token: str) -> bool:
        """
        EN: Releases the lock safely if the token matches.
        FA: آزادسازی ایمن قفل در صورتی که توکن مطابقت داشته باشد.
        """
        with self._manager_lock:
            if lock_key in self._owner_tokens and self._owner_tokens[lock_key] == token:
                self._release_lock_internal(lock_key)
                return True
            return False

    def _release_lock_internal(self, lock_key: str) -> None:
        """
        EN: Internal helper to release lock resources.
        FA: متد کمکی داخلی برای آزادسازی منابع قفل.
        """
        if lock_key in self._locks:
            lock = self._locks[lock_key]
            if lock.locked():
                try:
                    lock.release()
                except RuntimeError:
                    pass
            self._locks.pop(lock_key, None)
        self._owner_tokens.pop(lock_key, None)
        self._expires_at.pop(lock_key, None)


# EN: Singleton instance for local locks
# FA: نمونه سینگلتون برای قفل‌های محلی
local_lock_manager = LocalMemoryLockManager()


class DistributedLock:
    """
    EN: Redis-backed distributed lock with transparent fallback to local memory lock.
    FA: قفل توزیع‌شده مبتنی بر Redis با سوئیچ نامحسوس به قفل محلی در زمان قطع اتصال.
    """

    def __init__(self, redis_client: Optional[Any], lock_key: str) -> None:
        self.redis_client = redis_client
        self.lock_key = f"lock:{lock_key}"
        self.token: Optional[str] = None
        self._is_local = False

    def acquire(self, expire_sec: int = 10, timeout_sec: int = 5) -> bool:
        """
        EN: Acquires lock. Returns True on success, False on timeout/failure.
        FA: تلاش برای دریافت قفل. بازگرداندن True در صورت موفقیت و False در صورت شکست.
        """
        self.token = str(uuid.uuid4())

        if not self.redis_client:
            self._is_local = True
            local_token = local_lock_manager.try_acquire(self.lock_key, expire_sec, timeout_sec)
            if local_token:
                self.token = local_token
                return True
            return False

        start_time = time.time()
        while True:
            try:
                # EN: Try to SET NX EX
                # FA: تلاش برای ثبت قفل با ویژگی‌های انحصاری و انقضا در ردیس
                acquired = self.redis_client.set(
                    self.lock_key, self.token, ex=expire_sec, nx=True
                )
                if acquired:
                    return True
            except Exception as e:
                logger.warning(
                    f"Redis lock failed: {e}. Falling back to local lock.",
                    exc_info=True
                )
                self._is_local = True
                local_token = local_lock_manager.try_acquire(self.lock_key, expire_sec, timeout_sec)
                if local_token:
                    self.token = local_token
                    return True
                return False

            if timeout_sec <= 0 or (time.time() - start_time) >= timeout_sec:
                return False

            time.sleep(0.05)

    def release(self) -> bool:
        """
        EN: Releases the lock safely.
        FA: آزادسازی ایمن قفل.
        """
        if not self.token:
            return False

        if self._is_local or not self.redis_client:
            return local_lock_manager.release(self.lock_key, self.token)

        # EN: Lua script to ensure safe delete (only delete if value matches token)
        # FA: اسکریپت لوآ برای تضمین حذف ایمن قفل (فقط در صورت تطابق مقدار با توکن)
        lua_release = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        try:
            res = self.redis_client.eval(lua_release, 1, self.lock_key, self.token)
            return bool(res)
        except Exception as e:
            logger.error(f"Error releasing Redis lock: {e}", exc_info=True)
            # EN: Emergency fallback release locally just in case
            # FA: آزادسازی اضطراری قفل محلی در صورت بروز خطا
            return local_lock_manager.release(self.lock_key, self.token)
