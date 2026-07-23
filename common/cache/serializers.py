"""
EN: Pluggable serialization layer for the Cache Subsystem. Supports JSON and MessagePack.
FA: لایه سریالایزر پلاگبل برای زیرسیستم کش. پشتیبانی از JSON و MessagePack.
"""

import datetime
import json
import uuid
from abc import ABC, abstractmethod
from typing import Any

try:
    import msgpack
except ImportError:
    msgpack = None


class BaseCacheSerializer(ABC):
    """
    EN: Abstract base class for cache serialization.
    FA: کلاس پایه انتزاعی برای سریالایز کردن کش.
    """

    @abstractmethod
    def serialize(self, data: Any) -> bytes:
        """
        EN: Serializes python object into bytes.
        FA: تبدیل شیء پایتون به بایت.
        """
        pass

    @abstractmethod
    def deserialize(self, payload: bytes) -> Any:
        """
        EN: Deserializes bytes into python object.
        FA: تبدیل بایت به شیء پایتون.
        """
        pass


class CustomEncoder(json.JSONEncoder):
    """
    EN: Custom JSON encoder supporting datetime, date, UUID, and decimal.
    FA: انکودر سفارشی JSON برای پشتیبانی از datetime، date، UUID و decimal.
    """

    def default(self, o: Any) -> Any:
        if isinstance(o, (datetime.datetime, datetime.date)):
            return {"__datetime__": True, "value": o.isoformat()}
        if isinstance(o, uuid.UUID):
            return {"__uuid__": True, "value": str(o)}
        if hasattr(o, "tolist"):  # EN: NumPy arrays fallback
            return o.tolist()
        return super().default(o)


def custom_decoder(dct: dict) -> Any:
    """
    EN: Custom JSON decoder to reconstruct complex types from custom serialization markers.
    FA: دکودر سفارشی JSON برای بازسازی نوع‌های پیچیده از نشانگرهای سریالایزر سفارشی.
    """
    if "__datetime__" in dct:
        return datetime.datetime.fromisoformat(dct["value"])
    if "__uuid__" in dct:
        return uuid.UUID(dct["value"])
    return dct


class JSONSerializer(BaseCacheSerializer):
    """
    EN: Standard JSON Cache Serializer with custom datetime/UUID handlers.
    FA: سریالایزر استاندارد JSON کش با هندلرهای سفارشی برای datetime/UUID.
    """

    def serialize(self, data: Any) -> bytes:
        return json.dumps(data, cls=CustomEncoder).encode("utf-8")

    def deserialize(self, payload: bytes) -> Any:
        if not payload:
            return None
        return json.loads(payload.decode("utf-8"), object_hook=custom_decoder)


class MessagePackSerializer(BaseCacheSerializer):
    """
    EN: High-performance MessagePack Cache Serializer with fallback to JSON.
    FA: سریالایزر با کارایی بالای MessagePack برای کش به همراه جایگزین JSON در صورت نیاز.
    """

    def __init__(self) -> None:
        if msgpack is None:
            self._fallback = JSONSerializer()
        else:
            self._fallback = None

    def _pack_default(self, obj: Any) -> Any:
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return {"__datetime__": True, "value": obj.isoformat()}
        if isinstance(obj, uuid.UUID):
            return {"__uuid__": True, "value": str(obj)}
        raise TypeError(f"Type {type(obj)} not serializable in msgpack")

    def serialize(self, data: Any) -> bytes:
        if self._fallback:
            return self._fallback.serialize(data)
        try:
            return msgpack.packb(data, default=self._pack_default, use_bin_type=True)
        except Exception:
            # EN: Fallback to JSON in case of serialization failure
            # FA: جایگزین کردن با JSON در صورت شکست در سریالایز با msgpack
            return json.dumps(data, cls=CustomEncoder).encode("utf-8")

    def deserialize(self, payload: bytes) -> Any:
        if not payload:
            return None
        if self._fallback:
            return self._fallback.deserialize(payload)
        try:
            return msgpack.unpackb(payload, object_hook=custom_decoder, raw=False)
        except Exception:
            try:
                return json.loads(payload.decode("utf-8"), object_hook=custom_decoder)
            except Exception:
                return None
