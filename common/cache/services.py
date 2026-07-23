"""
EN: Predictive Prefetch and Warmup Services for the cache subsystem.
FA: سرویس‌های پیش‌گرم کردن کش (Warmup) و پیش‌خوانی پیش‌بینانه (Prefetch) برای زیرسیستم کش.
"""

import logging
import time
from typing import Any, Dict, List, Optional
import threading

from django.conf import settings
from .policies import build_cache_key
from .monitoring import metrics_tracker

logger = logging.getLogger(__name__)


class WarmupService:
    """
    EN: Warmup Service to pre-populate caches for critical CMS views on startup or content updates.
    FA: سرویس Warmup برای ثبت پیشاپیش کش‌های حیاتی CMS در زمان راه‌اندازی یا به‌روزرسانی محتوا.
    """

    def __init__(self, cache_manager_instance: Any) -> None:
        self.cache_manager = cache_manager_instance
        # EN: Keep track of registered warmup paths or builders
        # FA: ردیابی مسیرها یا سازنده‌های ثبت شده برای پیش‌گرم کردن کش
        self._builders: Dict[str, tuple] = {}

    def register_builder(self, name: str, key: str, callback: Any, group: Optional[str] = None, tags: Optional[List[str]] = None, soft_ttl: int = 300, hard_ttl: int = 600) -> None:
        """
        EN: Registers a data builder callback for a specific cache key.
        FA: ثبت کالبک سازنده داده برای یک کلید کش خاص.
        """
        self._builders[name] = (key, callback, group, tags, soft_ttl, hard_ttl)

    def trigger_warmup_for(self, name: str) -> bool:
        """
        EN: Regenerates the cache for a specific registered builder name.
        FA: بازسازی کش برای یک سازنده ثبت‌شده خاص.
        """
        if name not in self._builders:
            logger.warning(f"No warmup builder registered with name: {name}")
            return False

        key, callback, group, tags, soft_ttl, hard_ttl = self._builders[name]
        start_time = time.time()
        try:
            logger.info(f"Warming up cache for '{name}' with key '{key}'")
            # EN: Force regenerate the cache
            # FA: اجبار به بازسازی کش
            self.cache_manager.refresh(
                key=key,
                rebuild_callback=callback,
                group=group,
                tags=tags,
                soft_ttl_sec=soft_ttl,
                hard_ttl_sec=hard_ttl
            )
            duration = time.time() - start_time
            metrics_tracker.record_warmup(duration)
            return True
        except Exception as e:
            logger.error(f"Error warming up cache for '{name}': {e}", exc_info=True)
            return False

    def trigger_all_warmups(self) -> None:
        """
        EN: Runs all registered warmup builders.
        FA: اجرای تمامی سازنده‌های پیش‌گرم کردن کش ثبت‌شده.
        """
        logger.info("Starting global cache warmup process...")
        start_time = time.time()
        count = 0
        for name in list(self._builders.keys()):
            if self.trigger_warmup_for(name):
                count += 1
        duration = time.time() - start_time
        logger.info(f"Cache warmup completed. Warmed up {count}/{len(self._builders)} keys in {duration:.4f} seconds.")

    def warmup_after_mutation(self, article_slug: Optional[str] = None, category_slug: Optional[str] = None) -> None:
        """
        EN:
        Triggered after save/delete of Article/Category to regenerate:
        - Homepage
        - Specific Article Page
        - Category Page
        - Feeds

        FA:
        پس از ذخیره یا حذف مقاله/دسته‌بندی برای بازسازی خودکار موارد زیر فراخوانی می‌شود:
        - صفحه اصلی
        - صفحه مقاله خاص
        - صفحه دسته‌بندی
        - فیدها و نقشه‌های سایت
        """
        logger.info(f"Mutation detected (Article: {article_slug}, Category: {category_slug}). Triggering selective warmup.")

        # EN: Warm up homepage
        # FA: پیش‌گرم کردن صفحه اصلی
        if "homepage" in self._builders:
            self.trigger_warmup_for("homepage")

        # EN: Warm up feeds & category lists
        # FA: پیش‌گرم کردن فیدها و لیست دسته‌بندی‌ها
        if "categories_list" in self._builders:
            self.trigger_warmup_for("categories_list")

        # EN: Warm up specific mutated elements if builders exist
        # FA: پیش‌گرم کردن المان‌های تغییریافته خاص در صورت وجود سازنده
        if article_slug:
            builder_name = f"article_detail_{article_slug}"
            if builder_name in self._builders:
                self.trigger_warmup_for(builder_name)

            # EN: Related articles warmup
            # FA: پیش‌گرم کردن مقالات مرتبط
            related_name = f"related_articles_{article_slug}"
            if related_name in self._builders:
                self.trigger_warmup_for(related_name)

        if category_slug:
            cat_name = f"category_detail_{category_slug}"
            if cat_name in self._builders:
                self.trigger_warmup_for(cat_name)


class PrefetchService:
    """
    EN: Predictive Prefetch Service to refresh hot/frequently-accessed keys before hard-expiration.
    FA: سرویس پیش‌خوانی پیش‌بینانه جهت بازسازی کلیدهای پربازدید پیش از منقضی شدن کامل.
    """

    def __init__(self, cache_manager_instance: Any, check_interval_sec: int = 60) -> None:
        self.cache_manager = cache_manager_instance
        self.check_interval_sec = check_interval_sec
        self._hot_keys: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._is_running = False
        self._thread: Optional[threading.Thread] = None

    def register_hot_key(self, key: str, callback: Any, group: Optional[str] = None, tags: Optional[List[str]] = None, soft_ttl: int = 300, hard_ttl: int = 600) -> None:
        """
        EN: Registers a hot key for predictive prefetch tracking.
        FA: ثبت کلید پربازدید برای ردیابی و پیش‌خوانی پیش‌بینانه.
        """
        with self._lock:
            self._hot_keys[key] = {
                "callback": callback,
                "group": group,
                "tags": tags,
                "soft_ttl": soft_ttl,
                "hard_ttl": hard_ttl,
                "last_prefetched": time.time()
            }

    def start_background_loop(self) -> None:
        """
        EN: Starts background thread to periodically refresh hot keys.
        FA: شروع نخ پس‌زمینه برای بررسی و به‌روزرسانی دوره‌ای کلیدهای پربازدید.
        """
        with self._lock:
            if self._is_running:
                return
            self._is_running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True, name="cache-prefetch-loop")
            self._thread.start()
            logger.info("Predictive Prefetch background loop started.")

    def stop_background_loop(self) -> None:
        """
        EN: Stops predictive prefetch background thread.
        FA: توقف نخ پس‌زمینه پیش‌خوانی کش.
        """
        with self._lock:
            self._is_running = False
            logger.info("Predictive Prefetch background loop stopped.")

    def _run_loop(self) -> None:
        """
        EN: Periodic check loop for predictive prefetch.
        FA: حلقه بررسی دوره‌ای برای پیش‌خوانی پیش‌بینانه.
        """
        while self._is_running:
            try:
                time.sleep(self.check_interval_sec)
                self.run_predictive_prefetch()
            except Exception as e:
                logger.error(f"Error in Predictive Prefetch loop: {e}", exc_info=True)

    def run_predictive_prefetch(self) -> None:
        """
        EN: Iterates through registered hot keys and preemptively rebuilds them if close to expiration.
        FA: پیمایش کلیدهای پربازدید ثبت‌شده و بازسازی پیش‌دستانه آن‌ها در صورت نزدیکی به زمان انقضا.
        """
        logger.info("Running predictive prefetch sweep...")
        now = time.time()
        keys_to_prefetch = []

        with self._lock:
            for key, config in self._hot_keys.items():
                last_pref = config["last_prefetched"]
                soft_ttl = config["soft_ttl"]
                # EN: Prefetch if we are past 80% of soft TTL duration
                # FA: پیش‌خوانی در صورتی که بیش از ۸۰ درصد زمان انقضای نرم گذشته باشد
                if (now - last_pref) >= (soft_ttl * 0.8):
                    keys_to_prefetch.append((key, config))

        for key, config in keys_to_prefetch:
            try:
                logger.info(f"Predictive prefetch: refreshing hot key '{key}'")
                self.cache_manager.refresh(
                    key=key,
                    rebuild_callback=config["callback"],
                    group=config["group"],
                    tags=config["tags"],
                    soft_ttl_sec=config["soft_ttl"],
                    hard_ttl_sec=config["hard_ttl"]
                )
                with self._lock:
                    if key in self._hot_keys:
                        self._hot_keys[key]["last_prefetched"] = time.time()
            except Exception as e:
                logger.error(f"Failed predictive prefetch for key '{key}': {e}")


# EN: Global service singletons
# FA: نمونه‌های سرویس جهانی یکتا
warmup_service = WarmupService(None)  # EN: initialized in signal/manager wiring
prefetch_service = PrefetchService(None)
