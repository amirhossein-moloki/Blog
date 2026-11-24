"""
EN: Resilient, batch-capable client connecting Django Blog to Express Sayra Public GamingCenters APIs.
FA: کلاینت مقاوم و دسته‌ای برای اتصال وبلاگ جنگو به APIهای عمومی گیم‌نت در بک‌اند اکسپرس سایرا.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
from django.conf import settings
from django.core.cache import cache

from common.cache.locks import DistributedLock
from common.cache.manager import cache_manager

logger = logging.getLogger(__name__)

SAYRA_CACHE_VERSION_GROUP = "sayra_public_centers"
MAX_BATCH_IDS = 50

_http_session: Optional[requests.Session] = None


def get_http_session() -> requests.Session:
    """
    EN: Returns a shared requests.Session for connection pooling across calls.
    FA: یک نمونه مشترک requests.Session برای استفاده مجدد از اتصالات بازمی‌گرداند.
    """
    global _http_session
    if _http_session is None:
        _http_session = requests.Session()
    return _http_session


def _build_url(suffix: str) -> str:
    base = (
        getattr(settings, "SAYRA_API_BASE_URL", "http://sayra:3000/api/public") or ""
    ).rstrip("/")
    clean_suffix = suffix.lstrip("/")
    if base.endswith("/public"):
        return f"{base}/{clean_suffix}"
    return f"{base}/public/{clean_suffix}"


def _build_headers() -> Dict[str, str]:
    headers: Dict[str, str] = {"Accept": "application/json"}
    service_token = (getattr(settings, "SAYRA_SERVICE_TOKEN", "") or "").strip()
    ssr_secret = (getattr(settings, "SAYRA_SSR_SECRET", "") or "").strip()
    if service_token:
        headers["X-Service-Token"] = service_token
    if ssr_secret:
        headers["X-SSR-Secret"] = ssr_secret
    return headers


def _get_timeout() -> Tuple[float, float]:
    total = float(getattr(settings, "SAYRA_HTTP_TIMEOUT_SECONDS", 3.5) or 3.5)
    connect = min(2.0, total)
    return (connect, total)


def _fresh_ttl() -> int:
    return max(5, int(getattr(settings, "SAYRA_CACHE_FRESH_TTL_SECONDS", 120) or 120))


def _stale_ttl() -> int:
    return max(
        60, int(getattr(settings, "SAYRA_CACHE_STALE_TTL_SECONDS", 86400) or 86400)
    )


def get_sayra_cache_version() -> int:
    try:
        return cache_manager.invalidation.get_version(SAYRA_CACHE_VERSION_GROUP)
    except Exception:
        return 1


def bump_sayra_cache_version() -> int:
    try:
        return cache_manager.invalidation.increment_version(SAYRA_CACHE_VERSION_GROUP)
    except Exception as exc:
        logger.warning(f"Failed to bump Sayra cache version: {exc}")
        return 1


def _hash_params(kind: str, params: Dict[str, Any]) -> str:
    canonical = json.dumps(
        {"kind": kind, "params": params},
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


def _make_cache_keys(kind: str, params: Dict[str, Any]) -> Tuple[str, str]:
    param_hash = _hash_params(kind, params)
    version = get_sayra_cache_version()
    fresh_key = f"sayra:v{version}:{kind}:{param_hash}"
    stale_key = f"sayra:stale:{kind}:{param_hash}"
    return fresh_key, stale_key


def _fetch_with_cache_and_fallback(
    kind: str,
    url: str,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    fresh_key, stale_key = _make_cache_keys(kind, params)

    cached_fresh = cache.get(fresh_key)
    if isinstance(cached_fresh, dict) and "payload" in cached_fresh:
        return {
            "payload": cached_fresh["payload"],
            "source": "cache",
            "is_stale": False,
            "fetched_at": cached_fresh.get("fetched_at"),
        }

    lock_key = f"sayra_client:{_hash_params(kind, params)}"
    lock = DistributedLock(cache_manager._get_raw_client(), lock_key)
    acquired = lock.acquire(expire_sec=10, timeout_sec=2)
    try:
        if acquired:
            cached_after_lock = cache.get(fresh_key)
            if isinstance(cached_after_lock, dict) and "payload" in cached_after_lock:
                return {
                    "payload": cached_after_lock["payload"],
                    "source": "cache",
                    "is_stale": False,
                    "fetched_at": cached_after_lock.get("fetched_at"),
                }

        start = time.monotonic()
        resp = get_http_session().get(
            url,
            params=params,
            headers=_build_headers(),
            timeout=_get_timeout(),
        )
        duration_ms = round((time.monotonic() - start) * 1000, 1)

        if resp.status_code >= 400:
            logger.warning(
                "Sayra API returned error status",
                extra={
                    "kind": kind,
                    "status_code": resp.status_code,
                    "duration_ms": duration_ms,
                },
            )
            raise requests.HTTPError(
                f"Sayra API HTTP {resp.status_code}", response=resp
            )

        body = resp.json()
        payload = body.get("data", body) if isinstance(body, dict) else body
        fetched_at = datetime.now(timezone.utc).isoformat()
        envelope = {"payload": payload, "fetched_at": fetched_at}

        cache.set(fresh_key, envelope, timeout=_fresh_ttl())
        cache.set(stale_key, envelope, timeout=_stale_ttl())

        return {
            "payload": payload,
            "source": "live",
            "is_stale": False,
            "fetched_at": fetched_at,
        }
    except Exception as exc:
        logger.warning(
            f"Sayra API fetch failed ({kind}), checking stale fallback: {exc}"
        )
        stale_entry = cache.get(stale_key)
        if isinstance(stale_entry, dict) and "payload" in stale_entry:
            return {
                "payload": stale_entry["payload"],
                "source": "stale_cache",
                "is_stale": True,
                "fetched_at": stale_entry.get("fetched_at"),
            }
        return {
            "payload": None,
            "source": "unavailable",
            "is_stale": True,
            "fetched_at": None,
        }
    finally:
        if acquired:
            lock.release()


def get_centers_by_ids(center_ids: Iterable[str]) -> Dict[str, Any]:
    """
    EN: Fetches active & approved gaming centers in batch (up to 50 per HTTP request)
        to prevent N+1 queries and preserve caller ordering.
    FA: دریافت دسته‌ای اطلاعات گیم‌نت‌های فعال و تاییدشده (حداکثر ۵۰ شناسه در هر درخواست)
        برای جلوگیری از N+1 و حفظ ترتیب ارسالی.
    """
    ordered_unique_ids: List[str] = []
    seen = set()
    for raw_id in center_ids:
        clean = str(raw_id or "").strip()
        if clean and clean not in seen:
            seen.add(clean)
            ordered_unique_ids.append(clean)

    if not ordered_unique_ids:
        return {
            "items": [],
            "source": "live",
            "is_stale": False,
            "fetched_at": None,
        }

    url = _build_url("gamecenters")
    by_id: Dict[str, Dict[str, Any]] = {}
    sources: List[str] = []
    any_stale = False
    latest_fetched_at: Optional[str] = None

    for i in range(0, len(ordered_unique_ids), MAX_BATCH_IDS):
        chunk = ordered_unique_ids[i : i + MAX_BATCH_IDS]
        result = _fetch_with_cache_and_fallback(
            kind="batch_ids",
            url=url,
            params={"ids": ",".join(chunk)},
        )
        sources.append(result["source"])
        if result["is_stale"]:
            any_stale = True
        if result.get("fetched_at"):
            latest_fetched_at = result["fetched_at"]

        payload = result.get("payload")
        items_list: List[Dict[str, Any]] = []
        if isinstance(payload, dict) and isinstance(payload.get("data"), list):
            items_list = payload["data"]
        elif isinstance(payload, list):
            items_list = payload

        for item in items_list:
            if isinstance(item, dict) and item.get("id"):
                by_id[str(item["id"])] = item

    ordered_items = [by_id[cid] for cid in ordered_unique_ids if cid in by_id]
    overall_source = (
        "stale_cache"
        if "stale_cache" in sources
        else ("unavailable" if "unavailable" in sources and not ordered_items else sources[0])
    )
    return {
        "items": ordered_items,
        "source": overall_source,
        "is_stale": any_stale,
        "fetched_at": latest_fetched_at,
    }


def get_rankings(
    *,
    city: str = "",
    neighborhood: str = "",
    device_type: str = "",
    game: str = "",
    limit: int = 10,
    min_reviews: Optional[int] = None,
    m: Optional[float] = None,
    sort: str = "bayesian",
    include_newly_registered: bool = True,
) -> Dict[str, Any]:
    """
    EN: Fetches Bayesian-ranked and newly registered gaming centers from Express.
    FA: دریافت لیست رتبه‌بندی Bayesian و مراکز تازه‌ثبت‌شده از اکسپرس.
    """
    params: Dict[str, Any] = {
        "limit": limit,
        "sort": sort or "bayesian",
        "includeNewlyRegistered": "true" if include_newly_registered else "false",
    }
    if city and city.strip():
        params["city"] = city.strip()
    if neighborhood and neighborhood.strip():
        params["neighborhood"] = neighborhood.strip()
    if device_type and device_type.strip():
        params["deviceType"] = device_type.strip()
    if game and game.strip():
        params["game"] = game.strip()
    if min_reviews is not None:
        params["minReviews"] = int(min_reviews)
    if m is not None:
        params["m"] = float(m)

    url = _build_url("gamecenters/rankings")
    result = _fetch_with_cache_and_fallback(
        kind="rankings",
        url=url,
        params=params,
    )
    payload = result.get("payload")
    if not isinstance(payload, dict):
        payload = {
            "ranked": [],
            "newlyRegistered": [],
            "methodology": None,
        }

    return {
        "ranked": payload.get("ranked") or [],
        "newly_registered": payload.get("newlyRegistered") or [],
        "methodology": payload.get("methodology"),
        "source": result["source"],
        "is_stale": result["is_stale"],
        "fetched_at": result.get("fetched_at"),
    }


def resolve_article_gaming_centers(article: Any) -> Optional[Dict[str, Any]]:
    """
    EN: Resolves live gaming center cards for an Article according to its mode
        ('none', 'manual', or 'auto_ranking'), without duplicating mutable data in Django.
    FA: اطلاعات زنده گیم‌نت‌های مرتبط با یک مقاله را مطابق حالت مقاله استخراج و ترکیب می‌کند.
    """
    mode = getattr(article, "gaming_center_mode", "none") or "none"
    if mode == "none":
        return None

    links = list(article.gaming_center_links.all().order_by("display_order", "id"))
    editorial_by_id: Dict[str, Dict[str, Any]] = {
        str(link.gaming_center_id): {
            "display_order": link.display_order,
            "custom_description": link.custom_description or "",
        }
        for link in links
    }

    if mode == "manual":
        if not links:
            return {
                "mode": "manual",
                "items": [],
                "newly_registered": [],
                "methodology": None,
                "source": "live",
                "is_stale": False,
                "last_updated_at": None,
            }

        batch_res = get_centers_by_ids([link.gaming_center_id for link in links])
        enriched: List[Dict[str, Any]] = []
        for idx, center in enumerate(batch_res["items"]):
            cid = str(center.get("id", ""))
            editorial = editorial_by_id.get(cid, {})
            enriched.append(
                {
                    **center,
                    "display_order": editorial.get("display_order", idx),
                    "custom_description": editorial.get("custom_description", ""),
                }
            )
        enriched.sort(key=lambda item: (item.get("display_order", 0), str(item.get("id", ""))))
        return {
            "mode": "manual",
            "items": enriched,
            "newly_registered": [],
            "methodology": None,
            "source": batch_res["source"],
            "is_stale": batch_res["is_stale"],
            "last_updated_at": batch_res["fetched_at"],
        }

    # auto_ranking mode
    ranking_res = get_rankings(
        city=getattr(article, "ranking_city", "") or "",
        neighborhood=getattr(article, "ranking_neighborhood", "") or "",
        device_type=getattr(article, "ranking_device_type", "") or "",
        limit=getattr(article, "ranking_limit", 10) or 10,
        min_reviews=getattr(article, "ranking_min_reviews", None),
        m=getattr(article, "ranking_bayesian_m", None),
        sort=getattr(article, "ranking_sort", "bayesian") or "bayesian",
        include_newly_registered=bool(getattr(article, "include_newly_registered", True)),
    )

    def _attach_editorial(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for idx, center in enumerate(items):
            cid = str(center.get("id", ""))
            editorial = editorial_by_id.get(cid, {})
            out.append(
                {
                    **center,
                    "display_order": editorial.get("display_order", idx),
                    "custom_description": editorial.get("custom_description", ""),
                }
            )
        return out

    return {
        "mode": "auto_ranking",
        "items": _attach_editorial(ranking_res["ranked"]),
        "newly_registered": _attach_editorial(ranking_res["newly_registered"]),
        "methodology": ranking_res["methodology"],
        "source": ranking_res["source"],
        "is_stale": ranking_res["is_stale"],
        "last_updated_at": ranking_res["fetched_at"],
    }
