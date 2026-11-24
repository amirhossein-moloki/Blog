"""
EN: Authenticated HMAC-SHA256 webhook endpoint receiving GamingCenter change events from Sayra Express.
FA: اندپوینت وب‌هوک امن با امضای HMAC-SHA256 برای دریافت رویدادهای تغییر گیم‌نت از بک‌اند سایرا.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import List
from urllib.parse import quote

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.cache.manager import cache_manager
from posts.models import Article, ArticleTranslation
from posts.tasks import trigger_frontend_revalidation_task

from .sayra_client import bump_sayra_cache_version

logger = logging.getLogger(__name__)


def _verify_sayra_signature(raw_body: str, timestamp_raw: str, signature_raw: str) -> bool:
    secret = (getattr(settings, "SAYRA_WEBHOOK_SECRET", "") or "").strip()
    if not secret or not timestamp_raw or not signature_raw:
        return False

    try:
        timestamp_sec = int(str(timestamp_raw).strip())
    except (TypeError, ValueError):
        return False

    max_skew = int(getattr(settings, "SAYRA_WEBHOOK_MAX_SKEW_SECONDS", 300) or 300)
    if abs(int(time.time()) - timestamp_sec) > max_skew:
        return False

    digest = hmac.new(
        secret.encode("utf-8"),
        f"{timestamp_sec}.{raw_body}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    expected = f"sha256={digest}"
    return hmac.compare_digest(expected, signature_raw.strip())


class SayraEventWebhookView(APIView):
    """
    EN: Receives Express outbox events, invalidates Sayra/article caches, and triggers Next.js ISR.
    FA: دریافت رویدادهای Outbox اکسپرس، ابطال کش مقالات و ارسال درخواست بازسازی به Next.js.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        raw_bytes = request.body or b""
        try:
            raw_body = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return Response(
                {"detail": "Invalid UTF-8 body"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        signature = request.META.get("HTTP_X_SAYRA_SIGNATURE", "")
        timestamp_raw = request.META.get("HTTP_X_SAYRA_TIMESTAMP", "")

        if not _verify_sayra_signature(raw_body, timestamp_raw, signature):
            logger.warning("Rejected Sayra webhook due to missing/invalid HMAC signature")
            return Response(
                {"detail": "Invalid webhook signature"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            payload = json.loads(raw_body) if raw_body.strip() else {}
        except json.JSONDecodeError:
            return Response(
                {"detail": "Malformed JSON payload"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(payload, dict):
            return Response(
                {"detail": "JSON object expected"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        event_id = str(
            request.META.get("HTTP_X_SAYRA_EVENT_ID")
            or payload.get("outboxEventId")
            or payload.get("eventId")
            or ""
        ).strip()

        if event_id:
            dedupe_key = f"sayra:webhook:processed:{event_id}"
            if cache.get(dedupe_key):
                return Response(
                    {"accepted": True, "duplicate": True, "event_id": event_id},
                    status=status.HTTP_200_OK,
                )
            cache.set(dedupe_key, True, timeout=86400)

        gaming_center_id = str(payload.get("gamingCenterId") or "").strip()
        gaming_center_slug = str(payload.get("gamingCenterSlug") or "").strip()
        city = str(payload.get("city") or "").strip()
        event_type = str(payload.get("eventType") or "").strip()

        # 1. Immediately advance Sayra client cache version so fresh lookups fetch updated Express data
        bump_sayra_cache_version()

        # 2. Identify affected articles (manual links + auto-ranking articles matching city or global)
        article_query = Q()
        if gaming_center_id:
            article_query |= Q(gaming_center_links__gaming_center_id=gaming_center_id)

        if city:
            article_query |= Q(gaming_center_mode="auto_ranking", ranking_city__iexact=city)
            article_query |= Q(gaming_center_mode="auto_ranking", ranking_city="")
        else:
            article_query |= Q(gaming_center_mode="auto_ranking")

        affected_article_ids = list(
            Article.objects.filter(article_query).values_list("id", flat=True).distinct()
        )

        slugs: List[str] = []
        if affected_article_ids:
            slugs = list(
                ArticleTranslation.objects.filter(article_id__in=affected_article_ids)
                .values_list("slug", flat=True)
                .distinct()
            )
            for slug in slugs:
                cache_manager.invalidation.invalidate_tag(f"article_detail:{slug}")

        cache_manager.remove_by_version("articles")
        cache_manager.remove_by_version("latest_articles")
        cache_manager.remove_by_version("homepage")

        # 3. Trigger asynchronous Next.js ISR revalidation
        revalidation_paths = ["/blog"]
        for slug in slugs:
            revalidation_paths.append(f"/blog/{quote(str(slug), safe='')}")
        if gaming_center_slug:
            revalidation_paths.append(
                f"/gamecenter/{quote(gaming_center_slug, safe='')}"
            )

        revalidation_tags = ["blog-posts"]
        for slug in slugs:
            revalidation_tags.append(f"blog-post:{slug}")
        if gaming_center_id:
            revalidation_tags.append(f"gamecenter:{gaming_center_id}")

        try:
            trigger_frontend_revalidation_task.delay(
                paths=revalidation_paths,
                tags=revalidation_tags,
            )
        except Exception as exc:
            logger.warning(f"Could not queue Next.js revalidation task cleanly: {exc}")

        logger.info(
            "Processed Sayra webhook event",
            extra={
                "event_id": event_id,
                "event_type": event_type,
                "gaming_center_id": gaming_center_id,
                "city": city,
                "affected_articles": len(affected_article_ids),
            },
        )

        return Response(
            {
                "accepted": True,
                "duplicate": False,
                "event_id": event_id,
                "affected_articles": len(affected_article_ids),
                "revalidated_paths": revalidation_paths,
            },
            status=status.HTTP_200_OK,
        )
