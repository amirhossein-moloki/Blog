"""
EN: Multi-layer maintenance locking manager. Handles Redis (Primary) and Local File (Fallback) locking.
FA: مدیریت چندلایه‌ای قفل تعمیرات و نگهداری سیستم. پشتیبانی از ردیس (اصلی) و قفل محلی فایل (جایگزین).
"""

import fcntl
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)


class MaintenanceLockManager:
    """
    EN: Multi-layer maintenance lock manager.
    FA: مدیریت چندلایه‌ای قفل تعمیرات سیستم با قابلیت سوئیچ خودکار.
    """

    def __init__(self):
        self.redis_client = None
        self.redis_lock_key = "bdr:maintenance:lock"
        self.local_lock_path = Path(settings.BASE_DIR) / "bdr" / "maintenance.lock"
        self._local_lock_fd = None

        # Detect Redis and setup connection client
        if getattr(settings, "USE_REDIS", False) and getattr(
            settings, "REDIS_URL", None
        ):
            try:
                import redis

                self.redis_client = redis.from_url(
                    settings.REDIS_URL, decode_responses=True
                )
            except Exception as e:
                logger.warning(f"Failed to initialize direct Redis connection: {e}")

    def acquire_lock(self, owner="restore-system", ttl=600) -> bool:
        """
        EN: Tries to acquire the primary Redis lock. On failure/unavailability, falls back to local file lock.
        FA: تلاش برای دریافت قفل اولیه ردیس. در صورت خطا، سوئیچ خودکار به قفل فایل محلی اتمیک.
        """
        payload = {"owner": owner, "created": datetime.utcnow().isoformat(), "ttl": ttl}

        redis_success = False
        if self.redis_client:
            try:
                # EN: EX: expires in ttl seconds, NX: Set only if key does not exist
                # FA: تنظیم انقضا در ردیس به ثانیه و ثبت انحصاری مقدار در صورت عدم وجود کلید
                res = self.redis_client.set(
                    self.redis_lock_key, json.dumps(payload), ex=ttl, nx=True
                )
                if res:
                    redis_success = True
                    logger.info(
                        f"Successfully acquired primary Redis maintenance lock: {payload}"
                    )
            except Exception as e:
                logger.warning(
                    f"Redis is unavailable during acquire_lock: {e}. Falling back to local lock."
                )

        if not redis_success:
            # Fallback to local file lock
            self.local_lock_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                # EN: Atomic POSIX file creation (O_CREAT | O_EXCL)
                # FA: ایجاد اتمیک فایل به کمک فلگ‌های POSIX برای جلوگیری از ریسک همزمانی
                fd = os.open(
                    self.local_lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
                )
                try:
                    # EN: Apply POSIX exclusive non-blocking lock
                    # FA: اعمال قفل انحصاری غیرمسدودکننده برای اطمینان از سلامت فرآیند جاری
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

                    lock_info = {
                        "reason": "database_restore",
                        "started": datetime.utcnow().isoformat(),
                        "owner": owner,
                    }
                    os.write(fd, json.dumps(lock_info, indent=4).encode("utf-8"))
                    self._local_lock_fd = fd
                    logger.warning(
                        f"Redis fallback activated. Local maintenance lock created: {lock_info}"
                    )

                    from common.bdr_metrics import update_sre_metric

                    update_sre_metric(
                        "bdr_maintenance_fallback_used", 1, increment=True
                    )
                    return True
                except Exception as e:
                    os.close(fd)
                    try:
                        os.unlink(self.local_lock_path)
                    except OSError:
                        pass
                    raise e
            except (FileExistsError, OSError) as e:
                logger.error(f"Failed to acquire local file fallback lock: {e}")
                return False

        return True

    def release_lock(self) -> bool:
        """
        EN: Safely releases both Redis and Local lock layers.
        FA: آزادسازی ایمن قفل‌های فعال در هر دو لایه.
        """
        redis_released = False
        if self.redis_client:
            try:
                self.redis_client.delete(self.redis_lock_key)
                redis_released = True
            except Exception as e:
                logger.error(f"Failed to delete Redis maintenance lock: {e}")

        file_released = False
        if self._local_lock_fd is not None:
            try:
                fcntl.flock(self._local_lock_fd, fcntl.LOCK_UN)
                os.close(self._local_lock_fd)
            except Exception:
                pass
            self._local_lock_fd = None

        if self.local_lock_path.exists():
            try:
                os.unlink(self.local_lock_path)
                file_released = True
            except Exception as e:
                logger.error(f"Failed to delete local maintenance lock file: {e}")

        return redis_released or file_released

    def is_locked(self) -> bool:
        """
        EN: Detects if either primary Redis lock or local file fallback is currently active.
        FA: بررسی زنده بودن قفل در هر یک از لایه‌های ردیس یا قفل محلی فایل.
        """
        if self.redis_client:
            try:
                if self.redis_client.exists(self.redis_lock_key):
                    return True
            except Exception:
                pass

        if self.local_lock_path.exists():
            try:
                fd = os.open(self.local_lock_path, os.O_RDONLY)
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    # EN: If flock was successfully acquired, the previous process crashed/abandoned it!
                    # FA: در صورتی که قفل با موفقیت باز شد، یعنی پروسه قبلی کرش کرده و قفل دیگر معتبر نیست!
                    fcntl.flock(fd, fcntl.LOCK_UN)
                    os.close(fd)
                    try:
                        os.unlink(self.local_lock_path)
                    except OSError:
                        pass
                    return False
                except BlockingIOError:
                    # EN: File is actively locked by another process
                    # FA: فایل در حال حاضر توسط پروسه دیگری قفل است
                    os.close(fd)
                    return True
                except Exception:
                    os.close(fd)
                    return True
            except FileNotFoundError:
                return False

        return False

    def get_status(self) -> dict:
        """
        EN: Returns the status and owner details of active maintenance lock.
        FA: بازگرداندن وضعیت کلی قفل تعمیرات سیستم.
        """
        status = {
            "locked": False,
            "type": None,
            "owner": None,
            "created": None,
        }

        if self.redis_client:
            try:
                val = self.redis_client.get(self.redis_lock_key)
                if val:
                    data = json.loads(val)
                    status["locked"] = True
                    status["type"] = "redis"
                    status["owner"] = data.get("owner")
                    status["created"] = data.get("created")
                    return status
            except Exception:
                pass

        if self.local_lock_path.exists():
            try:
                fd = os.open(self.local_lock_path, os.O_RDONLY)
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    fcntl.flock(fd, fcntl.LOCK_UN)
                    os.close(fd)
                except BlockingIOError:
                    os.close(fd)
                    with open(self.local_lock_path, "r") as f:
                        data = json.load(f)
                    status["locked"] = True
                    status["type"] = "file"
                    status["owner"] = data.get("owner")
                    status["created"] = data.get("started")
                    return status
            except Exception:
                pass

        return status
