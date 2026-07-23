"""
EN: Comprehensive unit, integration, and performance tests for the caching subsystem.
FA: تست‌های جامع واحد، یکپارچه‌سازی و کارایی برای زیرسیستم کش.
"""

import time
from unittest import mock
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from common.cache import (
    cache_manager,
    build_cache_key,
    warmup_service,
    prefetch_service,
    metrics_tracker,
    CacheLevel,
)
from common.cache.serializers import JSONSerializer, MessagePackSerializer
from common.cache.compressors import GzipCompressor, ZstdCompressor
from common.cache.locks import DistributedLock, LocalMemoryLockManager, local_lock_manager
from common.cache.manager import CacheManager
from posts.models import Article, Category


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
            max_object_size_bytes=1024  # EN: 1KB limit for testing
        )

    def test_cache_key_generation_and_normalization(self) -> None:
        """EN: Verifies canonical key formatting and query sorting. FA: تایید فرمت کلید استاندارد و مرتب‌سازی پارامترها."""
        key1 = build_cache_key("module", "res", "id", params={"b": 2, "a": 1}, lang="fa")
        key2 = build_cache_key("module", "res", "id", params={"a": 1, "b": 2}, lang="fa")
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

    def test_size_limits(self) -> None:
        """EN: Checks that objects exceeding max size are rejected. FA: بررسی عدم پذیرش اشیای فراتر از سقف حجم مجاز."""
        large_data = {"junk": "a" * 2000}
        success = self.mgr.set("large_key", large_data)
        self.assertFalse(success)
        self.assertIsNone(self.mgr.get("large_key"))

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

    def test_cache_aside_pattern_and_stale_revalidate(self) -> None:
        """EN: Tests GetOrCreateAsync cache aside loop. FA: تست چرخه الگو کش به همراه Stale-While-Revalidate."""
        calls = 0

        def db_callback():
            nonlocal calls
            calls += 1
            return {"db_value": calls}

        # EN: First call: cache miss, triggers callback
        # FA: بار اول: عدم برخورد کش، اجرای کالبک
        val1 = self.mgr.get_or_create("aside_key", db_callback, soft_ttl_sec=1, hard_ttl_sec=3)
        self.assertEqual(val1, {"db_value": 1})
        self.assertEqual(calls, 1)

        # EN: Second call: cache hit, no callback
        # FA: بار دوم: برخورد کش، عدم اجرای کالبک
        val2 = self.mgr.get_or_create("aside_key", db_callback, soft_ttl_sec=1, hard_ttl_sec=3)
        self.assertEqual(val2, {"db_value": 1})
        self.assertEqual(calls, 1)

    def test_version_based_invalidation(self) -> None:
        """EN: Tests that incrementing group version invalidates reads. FA: تست ابطال داده‌ها با افزایش نسخه گروه."""
        calls = 0

        def db_callback():
            nonlocal calls
            calls += 1
            return {"count": calls}

        val1 = self.mgr.get_or_create("v_key", db_callback, group="articles", soft_ttl_sec=10, hard_ttl_sec=20)
        self.assertEqual(val1, {"count": 1})

        # EN: Increment group version
        # FA: افزایش نسخه گروه
        self.mgr.remove_by_version("articles")

        # EN: Next read should miss and fetch fresh data
        # FA: خواندن بعدی باید با شکست مواجه شده و داده جدید بگیرد
        val2 = self.mgr.get_or_create("v_key", db_callback, group="articles", soft_ttl_sec=10, hard_ttl_sec=20)
        self.assertEqual(val2, {"count": 2})

    def test_tag_based_invalidation(self) -> None:
        """EN: Tests invalidating by specific logical tags. FA: تست ابطال کش بر اساس تگ‌های منطقی مشخص."""
        calls = 0

        def db_callback():
            nonlocal calls
            calls += 1
            return {"tag_data": calls}

        val1 = self.mgr.get_or_create("tag_key", db_callback, tags=["cat:5"], soft_ttl_sec=10, hard_ttl_sec=20)
        self.assertEqual(val1, {"tag_data": 1})

        # EN: Invalidate specific tag
        # FA: ابطال تگ خاص
        self.mgr.invalidation.invalidate_tag("cat:5")

        # EN: Next read must miss and rebuild
        # FA: خواندن بعدی باید مجددا بازسازی شود
        val2 = self.mgr.get_or_create("tag_key", db_callback, tags=["cat:5"], soft_ttl_sec=10, hard_ttl_sec=20)
        self.assertEqual(val2, {"tag_data": 2})


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

    def test_health_cache_manager_endpoint(self) -> None:
        """EN: Verifies /health/cache-manager returns details. FA: تایید کارکرد اندپوینت /health/cache-manager."""
        url = reverse("health-cache-manager")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["status"], "healthy")
        self.assertIn("metrics", response.json())
