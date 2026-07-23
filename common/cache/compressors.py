"""
EN: Compression layer for cache payloads. Supports Gzip and optionally Zstandard.
FA: لایه فشرده‌سازی برای داده‌های کش. پشتیبانی از Gzip و به صورت اختیاری Zstandard.
"""

import gzip
from abc import ABC, abstractmethod

try:
    import zstandard as zstd
except ImportError:
    zstd = None


class BaseCacheCompressor(ABC):
    """
    EN: Abstract base class for cache compression.
    FA: کلاس پایه انتزاعی برای فشرده‌سازی کش.
    """

    @abstractmethod
    def compress(self, data: bytes) -> bytes:
        """
        EN: Compresses bytes payload.
        FA: فشرده‌سازی داده‌های بایتی.
        """
        pass

    @abstractmethod
    def decompress(self, payload: bytes) -> bytes:
        """
        EN: Decompresses bytes payload.
        FA: از حالت فشرده خارج کردن داده‌های بایتی.
        """
        pass


class GzipCompressor(BaseCacheCompressor):
    """
    EN: Standard Gzip Compressor.
    FA: فشرده‌ساز استاندارد Gzip.
    """

    def __init__(self, compress_level: int = 6) -> None:
        self.compress_level = compress_level

    def compress(self, data: bytes) -> bytes:
        return gzip.compress(data, compresslevel=self.compress_level)

    def decompress(self, payload: bytes) -> bytes:
        return gzip.decompress(payload)


class ZstdCompressor(BaseCacheCompressor):
    """
    EN: High-performance Zstandard Compressor with Gzip fallback.
    FA: فشرده‌ساز بسیار سریع و کارآمد Zstandard با جایگزین Gzip در صورت لزوم.
    """

    def __init__(self, level: int = 3) -> None:
        self.level = level
        if zstd is None:
            self._fallback = GzipCompressor()
        else:
            self._fallback = None

    def compress(self, data: bytes) -> bytes:
        if self._fallback:
            return self._fallback.compress(data)
        cctx = zstd.ZstdCompressor(level=self.level)
        return cctx.compress(data)

    def decompress(self, payload: bytes) -> bytes:
        if self._fallback:
            return self._fallback.decompress(payload)
        dctx = zstd.ZstdDecompressor()
        return dctx.decompress(payload)
