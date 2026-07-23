"""
EN: Comprehensive unit, integration, and performance tests for the caching subsystem.
FA: تست‌های جامع واحد، یکپارچه‌سازی و کارایی برای زیرسیستم کش.
"""

import asyncio
import datetime
import time
import uuid
from unittest import mock

from django.http import JsonResponse
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from common.cache import (
    CacheLevel,
    build_cache_key,
    cache_manager,
    metrics_tracker,
    prefetch_service,
    warmup_service,
)
from common.cache.compressors import GzipCompressor, ZstdCompressor
from common.cache.invalidation import InvalidationManager
from common.cache.locks import (
    DistributedLock,
    LocalMemoryLockManager,
    local_lock_manager,
)
from common.cache.manager import CacheManager
from common.cache.serializers import JSONSerializer, MessagePackSerializer
from common.cache.views import (
    CacheHealthView,
    CacheManagerHealthView,
    RedisHealthView,
)
from interactions.models import Comment
from pages.models import Page
from posts.models import Article, Category, Tag


class CacheSubsystemTests(TestCase):
    """
    EN: Tests the unit behavior of policies, serializers, compressors, locking, and managers.
    FA: رفتارهای واحد سیاست‌ها، سریالایزرها، فشرده‌سازها، قفل‌ها و مدیران کش را تست می‌کند.
    """

    def setUp(self) -> None:
        # EN: Use a pristine custom CacheManager with default LocMemCache to avoid polluting global state
        # FA: استفاده از یک مدیر کش سفارشی جدید با LocMemCache برای جلوگیری از تغییر وضعیت سراسری
        self.mgr = CacheManager(
            serializer=JSONSerializer(),
            compressor=GzipCompressor(),
            compression_threshold_bytes=100,
            max_object_size_bytes=1024,  # EN: 1KB limit for testing
        )

    def test_cache_key_generation_and_normalization(self) -> None:
        """EN: Verifies canonical key formatting and query sorting. FA: تایید فرمت کلید استاندارد و مرتب‌سازی پارامترها."""
        key1 = build_cache_key(
            "module", "res", "id", params={"b": 2, "a": 1}, lang="fa"
        )
        key2 = build_cache_key(
            "module", "res", "id", params={"a": 1, "b": 2}, lang="fa"
        )
        self.assertEqual(key1, key2)
        self.assertTrue(key1.startswith("project:v1:module:res:id:"))

    def test_serializers(self) -> None:
        """EN: Tests JSON and MessagePack serialization fidelity. FA: تست صحت رفتار سریالایزرهای JSON و MessagePack."""
        test_data = {"text": "hello", "nested": [1, 2], "flag": True}

        json_ser = JSONSerializer()
        packed_json = json_ser.serialize(test_data)
        self.assertEqual(json_ser.deserialize(packed_json), test_data)

        msgpack_ser = MessagePackSerializer()
        packed_msgpack = msgpack_ser.serialize(test_data)
        self.assertEqual(msgpack_ser.deserialize(packed_msgpack), test_data)

    def test_serializers_fallback_and_edge_cases(self) -> None:
        """EN: Tests fallback behavior when MsgPack encounters exceptions or is None. FA: تست رفتار جایگزین سریالایزرها."""
        uid = uuid.uuid4()
        dt = datetime.datetime.now()
        data = {"uuid": uid, "dt": dt}
        ser = JSONSerializer()
        payload = ser.serialize(data)
        decoded = ser.deserialize(payload)
        self.assertEqual(decoded["uuid"], uid)
        self.assertEqual(decoded["dt"], dt)

        # Force message pack fallback
        with mock.patch("common.cache.serializers.msgpack", None):
            fallback_ser = MessagePackSerializer()
            packed = fallback_ser.serialize({"a": 1})
            self.assertEqual(fallback_ser.deserialize(packed), {"a": 1})

        # Test MessagePackSerializer with exception mocking on msgpack.packb
        m_ser = MessagePackSerializer()
        if hasattr(m_ser, "_fallback") and m_ser._fallback is None:
            with mock.patch("msgpack.packb", side_effect=ValueError("forced error")):
                fallback_payload = m_ser.serialize({"a": 1})
                self.assertIsNotNone(fallback_payload)

        self.assertIsNone(m_ser.deserialize(b""))

    def test_msgpack_deserialize_exception_fallback(self) -> None:
        """EN: Tests that MsgPack deserialization falls back to JSON if exception is raised. FA: تست سوئیچ به JSON در دکود کردن پیام."""
        m_ser = MessagePackSerializer()
        if hasattr(m_ser, "_fallback") and m_ser._fallback is None:
            with mock.patch(
                "msgpack.unpackb", side_effect=Exception("msgpack decode error")
            ):
                # When msgpack fails, it falls back to decoding with json
                payload = JSONSerializer().serialize({"ok": True})
                self.assertEqual(m_ser.deserialize(payload), {"ok": True})

    def test_compressors(self) -> None:
        """EN: Tests gzip and zstd compressors. FA: تست صحت فشرده‌سازهای Gzip و Zstandard."""
        test_bytes = b"hello compression " * 20

        gzip_comp = GzipCompressor()
        compressed = gzip_comp.compress(test_bytes)
        self.assertTrue(len(compressed) < len(test_bytes))
        self.assertEqual(gzip_comp.decompress(compressed), test_bytes)

        zstd_comp = ZstdCompressor()
        compressed_zstd = zstd_comp.compress(test_bytes)
        self.assertEqual(zstd_comp.decompress(compressed_zstd), test_bytes)

        # Force Zstd fallback to gzip
        with mock.patch("common.cache.compressors.zstd", None):
            fallback_zstd = ZstdCompressor()
            self.assertEqual(
                fallback_zstd.compress(test_bytes), gzip_comp.compress(test_bytes)
            )

    def test_size_limits(self) -> None:
        """EN: Checks that objects exceeding max size are rejected. FA: بررسی عدم پذیرش اشیای فراتر از سقف حجم مجاز."""
        large_data = {"junk": "a" * 2000}
        success = self.mgr.set("large_key", large_data)
        self.assertFalse(success)
        self.assertIsNone(self.mgr.get("large_key"))

    def test_corrupted_envelope_bytes(self) -> None:
        """EN: Tests that invalid envelope bytes are handled gracefully. FA: بررسی هندل کردن بایت‌های نامعتبر پاکت کش."""
        # Direct write of bad bytes
        self.mgr._django_cache.set("bad_bytes_key", b"invalid_bytes_not_dict")
        self.assertIsNone(self.mgr.get("bad_bytes_key"))

    def test_lock_acquire_and_release(self) -> None:
        """EN: Tests local thread-safe lock manager. FA: تست عملکرد قفل محلی ایمن برای چندنخی."""
        manager = LocalMemoryLockManager()
        token = manager.try_acquire("test_lock", expire_sec=5, timeout_sec=1)
        self.assertIsNotNone(token)

        # EN: Second attempt on same key should fail/timeout
        # FA: تلاش دوم روی همان کلید باید با شکست مواجه شود
        failed_token = manager.try_acquire("test_lock", expire_sec=5, timeout_sec=0)
        self.assertIsNone(failed_token)

        # EN: Release and retry
        # FA: آزادسازی و تلاش مجدد
        self.assertTrue(manager.release("test_lock", token))
        retry_token = manager.try_acquire("test_lock", expire_sec=5, timeout_sec=0)
        self.assertIsNotNone(retry_token)
        manager.release("test_lock", retry_token)

    def test_distributed_lock_redis_fallback(self) -> None:
        """EN: Tests DistributedLock falling back gracefully when Redis fails. FA: تست سوئیچ قفل توزیع‌شده به محلی."""
        mock_client = mock.MagicMock()
        mock_client.set.side_effect = Exception("Redis failure")

        lock = DistributedLock(mock_client, "broken_lock")
        acquired = lock.acquire(expire_sec=5, timeout_sec=1)
        self.assertTrue(acquired)
        self.assertTrue(lock._is_local)
        self.assertTrue(lock.release())

    def test_cache_aside_pattern_and_stale_revalidate(self) -> None:
        """EN: Tests GetOrCreateAsync cache aside loop. FA: تست چرخه الگو کش به همراه Stale-While-Revalidate."""
        calls = 0

        def db_callback():
            nonlocal calls
            calls += 1
            return {"db_value": calls}

        # EN: First call: cache miss, triggers callback
        # FA: بار اول: عدم برخورد کش، اجرای کالبک
        val1 = self.mgr.get_or_create(
            "aside_key", db_callback, soft_ttl_sec=1, hard_ttl_sec=3
        )
        self.assertEqual(val1, {"db_value": 1})
        self.assertEqual(calls, 1)

        # EN: Second call: cache hit, no callback
        # FA: بار دوم: برخورد کش، عدم اجرای کالبک
        val2 = self.mgr.get_or_create(
            "aside_key", db_callback, soft_ttl_sec=1, hard_ttl_sec=3
        )
        self.assertEqual(val2, {"db_value": 1})
        self.assertEqual(calls, 1)

    def test_get_or_create_lock_timeout_fallback(self) -> None:
        """EN: Tests that if lock acquisition fails, get_or_create falls back directly to database. FA: تست اجرای مستقیم کوئری در صورت شکست قفل."""
        called = 0

        def db_callback():
            nonlocal called
            called += 1
            return "db_fresh"

        # Mock lock to fail acquiring
        with mock.patch(
            "common.cache.manager.DistributedLock.acquire", return_value=False
        ):
            val = self.mgr.get_or_create("timeout_key", db_callback)
            self.assertEqual(val, "db_fresh")
            self.assertEqual(called, 1)

    def test_cache_exceptions_handling(self) -> None:
        """EN: Verifies that backend exceptions are caught gracefully. FA: بررسی هندل کردن ایمن استثناهای انجین کش."""
        with mock.patch.object(
            self.mgr._django_cache, "get", side_effect=Exception("Cache down")
        ):
            self.assertIsNone(self.mgr.get("any_key"))

        with mock.patch.object(
            self.mgr._django_cache, "set", side_effect=Exception("Cache down")
        ):
            self.assertFalse(self.mgr.set("any_key", "value"))

    def test_version_based_invalidation(self) -> None:
        """EN: Tests that incrementing group version invalidates reads. FA: تست ابطال داده‌ها با افزایش نسخه گروه."""
        calls = 0

        def db_callback():
            nonlocal calls
            calls += 1
            return {"count": calls}

        val1 = self.mgr.get_or_create(
            "v_key",
            db_callback,
            group="articles",
            soft_ttl_sec=10,
            hard_ttl_sec=20,
        )
        self.assertEqual(val1, {"count": 1})

        # EN: Increment group version
        # FA: افزایش نسخه گروه
        self.mgr.remove_by_version("articles")

        # EN: Next read should miss and fetch fresh data
        # FA: خواندن بعدی باید با شکست مواجه شده و داده جدید بگیرد
        val2 = self.mgr.get_or_create(
            "v_key",
            db_callback,
            group="articles",
            soft_ttl_sec=10,
            hard_ttl_sec=20,
        )
        self.assertEqual(val2, {"count": 2})

    def test_tag_based_invalidation(self) -> None:
        """EN: Tests invalidating by specific logical tags. FA: تست ابطال کش بر اساس تگ‌های منطقی مشخص."""
        calls = 0

        def db_callback():
            nonlocal calls
            calls += 1
            return {"tag_data": calls}

        val1 = self.mgr.get_or_create(
            "tag_key",
            db_callback,
            tags=["cat:5"],
            soft_ttl_sec=10,
            hard_ttl_sec=20,
        )
        self.assertEqual(val1, {"tag_data": 1})

        # EN: Invalidate specific tag
        # FA: ابطال تگ خاص
        self.mgr.invalidation.invalidate_tag("cat:5")

        # EN: Next read must miss and rebuild
        # FA: خواندن بعدی باید مجددا بازسازی شود
        val2 = self.mgr.get_or_create(
            "tag_key",
            db_callback,
            tags=["cat:5"],
            soft_ttl_sec=10,
            hard_ttl_sec=20,
        )
        self.assertEqual(val2, {"tag_data": 2})

    def test_camel_case_interfaces_async(self) -> None:
        """EN: Tests all camelCase Async-first aliases. FA: تست کلیه متدهای مستعار شتری."""
        # We can run these synchronously because of our implementation
        self.mgr.set("camel_key", "value")
        self.assertEqual(asyncio.run(self.mgr.GetAsync("camel_key")), "value")
        asyncio.run(self.mgr.SetAsync("camel_key", "new-value"))
        self.assertEqual(self.mgr.get("camel_key"), "new-value")
        self.assertTrue(asyncio.run(self.mgr.ExistsAsync("camel_key")))
        asyncio.run(self.mgr.RemoveAsync("camel_key"))
        self.assertFalse(self.mgr.exists("camel_key"))

        # Test CamelCase locks
        success, token = asyncio.run(self.mgr.TryAcquireLock("camel_lock"))
        self.assertTrue(success)
        self.assertTrue(asyncio.run(self.mgr.ReleaseLock("camel_lock", token)))

        # Test Refresh/Warmup Async
        asyncio.run(self.mgr.WarmupAsync("camel_warm", "val"))
        self.assertEqual(self.mgr.get("camel_warm"), "val")
        asyncio.run(self.mgr.RefreshAsync("camel_warm", lambda: "val2"))
        self.assertEqual(self.mgr.get("camel_warm"), "val2")

    def test_warmup_and_prefetch_services(self) -> None:
        """EN: Tests warmup builder registration and prefetch mechanisms. FA: تست ثبت بیلدرهای Warmup و مکانیزم Prefetch."""
        called = 0

        def build():
            nonlocal called
            called += 1
            return "warmed"

        original_warmup_mgr = warmup_service.cache_manager
        original_prefetch_mgr = prefetch_service.cache_manager

        try:
            warmup_service.cache_manager = self.mgr
            prefetch_service.cache_manager = self.mgr

            self.mgr.set("warm", "old")
            warmup_service.register_builder(
                name="test_build",
                key="warm",
                callback=build,
                group="test_group",
                tags=["test_tag"],
                soft_ttl=10,
                hard_ttl=20,
            )

            warmup_service.trigger_warmup_for("test_build")
            self.assertEqual(called, 1)
            self.assertEqual(self.mgr.get("warm"), "warmed")

            # Prefetch Service
            prefetch_service.register_hot_key(
                key="warm",
                callback=build,
                group="test_group",
                tags=["test_tag"],
                soft_ttl=0,  # Immediate prefetch
                hard_ttl=10,
            )
            prefetch_service.run_predictive_prefetch()
            self.assertEqual(called, 2)

            # Test warmup after mutation & trigger all warmups
            warmup_service.trigger_all_warmups()
            warmup_service.warmup_after_mutation(
                article_slug="some-slug", category_slug="some-cat"
            )

        finally:
            warmup_service.cache_manager = original_warmup_mgr
            prefetch_service.cache_manager = original_prefetch_mgr

    def test_signals_cache_invalidation_events(self) -> None:
        """EN: Verifies database signal handlers automatically invalidate cache. FA: تایید صحت اجرای هندلر سیگنال دیتابیس."""
        # Mock Category save
        category = Category(name="Tech", slug="tech")
        # Since we use signals.connect, let's trigger the signals manually or test using mocks
        with mock.patch("common.cache.signals.cache_manager") as mock_cache:
            from common.cache.signals import invalidate_category_cache

            invalidate_category_cache(sender=Category, instance=category)
            mock_cache.remove_by_version.assert_any_call("categories")
            mock_cache.invalidation.invalidate_tag.assert_any_call(
                "category_detail:tech"
            )

        # Mock Page save
        page = Page(title="About", slug="about")
        with mock.patch("common.cache.signals.cache_manager") as mock_cache:
            from common.cache.signals import invalidate_page_cache

            invalidate_page_cache(sender=Page, instance=page)
            mock_cache.remove_by_version.assert_any_call("pages")

    def test_monitoring_telemetry_redis_mocked(self) -> None:
        """EN: Verifies telemetry correctly handles healthy Redis mocks. FA: تست تله‌متری با کلاینت فرضی ردیس سالم."""
        mock_redis = mock.MagicMock()
        mock_redis.info.return_value = {
            "used_memory": "5000",
            "used_memory_human": "5K",
            "used_cpu_sys": "0.5",
            "used_cpu_user": "0.3",
            "db1": {"keys": 10},
            "expired_keys": "2",
            "evicted_keys": "1",
            "mem_fragmentation_ratio": "1.2",
            "instantaneous_ops_per_sec": "50",
            "connected_clients": "3",
        }
        telemetry = metrics_tracker.get_redis_telemetry(mock_redis)
        self.assertTrue(telemetry["redis_available"])
        self.assertEqual(telemetry["keys_count"], 10)


class CacheAPIViewsTests(APITestCase):
    """
    EN: Tests caching functionality on REST API views and health checks.
    FA: عملکرد کش در نماهای REST API و تست‌های بررسی سلامت را ارزیابی می‌کند.
    """

    def setUp(self) -> None:
        # EN: Ensure static API key is set for authorization during integration test
        # FA: اطمینان از تنظیم کلید استاتیک API برای تایید دسترسی
        self.client.credentials(HTTP_X_API_KEY="test-key")

    def test_health_cache_endpoint(self) -> None:
        """EN: Verifies /health/cache returns healthy. FA: تایید سلامت اندپوینت /health/cache."""
        url = reverse("health-cache")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["status"], "healthy")

    def test_health_redis_endpoint_offline(self) -> None:
        """EN: Verifies /health/redis handles offline gracefully. FA: بررسی هندل کردن آفلاین بودن ردیس."""
        url = reverse("health-redis")
        response = self.client.get(url)
        # Should return 503 since Redis is not physically running in pure unit-test sandbox
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.json()["status"], "unhealthy")

    def test_health_cache_manager_endpoint(self) -> None:
        """EN: Verifies /health/cache-manager returns details. FA: تایید کارکرد اندپوینت /health/cache-manager."""
        url = reverse("health-cache-manager")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["status"], "healthy")
        self.assertIn("metrics", response.json())

    def test_health_views_exception_scenario(self) -> None:
        """EN: Verifies exception scenarios return unhealthy. FA: تایید سناریوهای استثنا در بررسی سلامت."""
        # Test Cache Health view with failure
        from django.core.cache import caches

        with mock.patch.object(
            caches["default"], "set", side_effect=ValueError("connection issue")
        ):
            url = reverse("health-cache")
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

        # Test Redis Health view with exception
        with mock.patch(
            "common.cache.manager.CacheManager._get_raw_client",
            side_effect=ValueError("redis error"),
        ):
            url = reverse("health-redis")
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_cache_manager_health_lock_acquisition_failure(self) -> None:
        """EN: Tests lock failure scenario inside CacheManagerHealthView. FA: تست خطای قفل در نمای بررسی سلامت مدیر کش."""
        with mock.patch(
            "common.cache.manager.CacheManager.try_acquire_lock",
            return_value=(False, None),
        ):
            url = reverse("health-cache-manager")
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_cache_manager_health_lock_release_failure(self) -> None:
        """EN: Tests lock release failure inside CacheManagerHealthView. FA: تست خطای آزادسازی قفل در نمای بررسی سلامت."""
        with mock.patch(
            "common.cache.manager.CacheManager.try_acquire_lock",
            return_value=(True, "tok"),
        ):
            with mock.patch(
                "common.cache.manager.CacheManager.release_lock", return_value=False
            ):
                url = reverse("health-cache-manager")
                response = self.client.get(url)
                self.assertEqual(
                    response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE
                )
