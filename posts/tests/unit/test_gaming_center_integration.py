import hashlib
import hmac
import json
import time
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import requests
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from posts.integrations.sayra_client import (
    bump_sayra_cache_version,
    get_centers_by_ids,
    get_rankings,
    resolve_article_gaming_centers,
)
from posts.models import (
    Article,
    ArticleGamingCenter,
    ArticleTranslation,
    AuthorProfile,
    Category,
)
from posts.serializers import ArticleCreateUpdateSerializer, ArticleDetailSerializer

User = get_user_model()


def _make_sayra_center(cid: str, name: str, rating: float = 4.6, reviews: int = 4):
    return {
        "id": cid,
        "name": name,
        "slug": f"slug-{cid}",
        "city": "تبریز",
        "neighborhood": "ولیعصر",
        "address": "تبریز، ولیعصر",
        "images": {"coverUrl": "https://cdn.example.com/c.webp", "gallery": []},
        "devices": [],
        "deviceCounts": {
            "PC": 10,
            "PLAYSTATION 4": 0,
            "PLAYSTATION 5": 5,
            "XBOX": 0,
            "SWITCH": 0,
            "VR": 0,
        },
        "pcCount": 10,
        "consoleCount": 5,
        "amenities": ["vip", "food_service"],
        "games": ["FC 25"],
        "pricing": {
            "startingHourlyRate": 120000,
            "originalPrice": 120000,
            "finalPrice": 120000,
            "hasDiscount": False,
            "discountPercentage": 0,
            "discountAmount": 0,
            "currency": "IRT",
        },
        "activityStatus": {
            "isActive": True,
            "isOpenNow": True,
            "openingTime": "10:00",
            "closingTime": "23:59",
            "timezone": "Asia/Tehran",
            "isTemporarilyClosed": False,
            "closedUntil": None,
        },
        "rating": {
            "average": rating,
            "validReviewsCount": reviews,
            "latestReviewAt": "2026-10-01T10:00:00Z",
        },
        "ranking": None,
        "detailUrl": f"/gamecenter/slug-{cid}",
        "absoluteDetailUrl": f"https://www.sayra-booking.ir/gamecenter/slug-{cid}",
        "updatedAt": "2026-10-01T10:00:00Z",
    }


@override_settings(
    SAYRA_API_BASE_URL="http://sayra:3000/api/public",
    SAYRA_SERVICE_TOKEN="test-service-token",
    SAYRA_SSR_SECRET="test-ssr-secret",
    SAYRA_WEBHOOK_SECRET="test-webhook-secret",
    SAYRA_WEBHOOK_MAX_SKEW_SECONDS=300,
    SAYRA_CACHE_FRESH_TTL_SECONDS=120,
    SAYRA_CACHE_STALE_TTL_SECONDS=86400,
    NEXT_REVALIDATE_URL="",
    NEXT_REVALIDATION_SECRET="",
)
class GamingCenterIntegrationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="blog_editor", password="StrongPassword123!"
        )
        self.author = AuthorProfile.objects.create(
            user=self.user, display_name="تحریریه سایرا"
        )
        self.category = Category.objects.create(name="تبریز", slug="tabriz-guides")

    def test_article_gaming_center_model_no_mutable_duplication_and_unique_constraint(self):
        field_names = {f.name for f in ArticleGamingCenter._meta.get_fields()}
        for forbidden in ("name", "hourly_rate", "address", "rating", "amenities", "images"):
            self.assertNotIn(forbidden, field_names)

        article = Article.objects.create(
            author=self.author,
            category=self.category,
            status="draft",
            gaming_center_mode="manual",
        )
        ArticleGamingCenter.objects.create(
            article=article,
            gaming_center_id="center_02",
            display_order=1,
            custom_description="توضیح دوم",
        )
        ArticleGamingCenter.objects.create(
            article=article,
            gaming_center_id="center_01",
            display_order=0,
            custom_description="توضیح اول",
        )

        links = list(article.gaming_center_links.all())
        self.assertEqual([l.gaming_center_id for l in links], ["center_01", "center_02"])

        with self.assertRaises(IntegrityError):
            ArticleGamingCenter.objects.create(
                article=article,
                gaming_center_id="center_01",
                display_order=2,
            )

    def test_manual_mode_uses_single_batch_call_and_drops_unverified_centers(self):
        article = Article.objects.create(
            author=self.author,
            category=self.category,
            status="published",
            gaming_center_mode="manual",
        )
        ArticleTranslation.objects.create(
            article=article,
            language_code="fa",
            slug="manual-tabriz-picks",
            title="گیم‌نت‌های منتخب تبریز",
            excerpt="خلاصه",
        )
        ArticleGamingCenter.objects.create(
            article=article,
            gaming_center_id="gc-2",
            display_order=0,
            custom_description="انتخاب اول تحریریه",
        )
        ArticleGamingCenter.objects.create(
            article=article,
            gaming_center_id="gc-1",
            display_order=1,
            custom_description="انتخاب دوم تحریریه",
        )
        ArticleGamingCenter.objects.create(
            article=article,
            gaming_center_id="gc-unverified",
            display_order=2,
            custom_description="نباید نمایش داده شود",
        )

        # Express omits gc-unverified because it is inactive/unapproved
        mock_response = SimpleNamespace(
            status_code=200,
            json=lambda: {
                "success": True,
                "data": {
                    "data": [
                        _make_sayra_center("gc-2", "مرکز دو"),
                        _make_sayra_center("gc-1", "مرکز یک"),
                    ],
                    "meta": {"total": 2, "page": 1, "limit": 3, "totalPages": 1},
                },
            },
        )
        mock_session = MagicMock()
        mock_session.get.return_value = mock_response

        with patch(
            "posts.integrations.sayra_client.get_http_session",
            return_value=mock_session,
        ):
            section = resolve_article_gaming_centers(article)

        self.assertEqual(mock_session.get.call_count, 1)
        call_kwargs = mock_session.get.call_args.kwargs
        self.assertEqual(call_kwargs["params"]["ids"], "gc-2,gc-1,gc-unverified")
        self.assertEqual(call_kwargs["headers"]["X-Service-Token"], "test-service-token")
        self.assertEqual(call_kwargs["headers"]["X-SSR-Secret"], "test-ssr-secret")

        self.assertIsNotNone(section)
        self.assertEqual(section["mode"], "manual")
        self.assertEqual([item["id"] for item in section["items"]], ["gc-2", "gc-1"])
        self.assertEqual(section["items"][0]["custom_description"], "انتخاب اول تحریریه")
        self.assertEqual(section["items"][1]["display_order"], 1)

    def test_auto_ranking_mode_separates_ranked_and_newly_registered(self):
        article = Article.objects.create(
            author=self.author,
            category=self.category,
            status="draft",
            gaming_center_mode="auto_ranking",
            ranking_city="تبریز",
            ranking_limit=10,
            ranking_min_reviews=3,
            ranking_bayesian_m=3.0,
            ranking_sort="bayesian",
            include_newly_registered=True,
        )

        mock_response = SimpleNamespace(
            status_code=200,
            json=lambda: {
                "success": True,
                "data": {
                    "ranked": [_make_sayra_center("gc-ranked-1", "برترین تبریز", 4.9, 10)],
                    "newlyRegistered": [_make_sayra_center("gc-new-1", "تازه‌ثبت تبریز", 5.0, 1)],
                    "methodology": {
                        "algorithm": "bayesian_average",
                        "m": 3,
                        "minReviews": 3,
                        "globalAverageC": 4.6,
                    },
                },
            },
        )
        mock_session = MagicMock()
        mock_session.get.return_value = mock_response

        with patch(
            "posts.integrations.sayra_client.get_http_session",
            return_value=mock_session,
        ):
            serializer = ArticleDetailSerializer(article)
            section = serializer.data["gaming_centers_section"]

        self.assertEqual(section["mode"], "auto_ranking")
        self.assertEqual([c["id"] for c in section["items"]], ["gc-ranked-1"])
        self.assertEqual([c["id"] for c in section["newly_registered"]], ["gc-new-1"])
        self.assertEqual(section["methodology"]["algorithm"], "bayesian_average")

    def test_cache_hit_and_stale_fallback_when_express_fails(self):
        mock_response = SimpleNamespace(
            status_code=200,
            json=lambda: {
                "success": True,
                "data": {
                    "data": [_make_sayra_center("gc-cached", "مرکز کش‌شده")],
                    "meta": {"total": 1, "page": 1, "limit": 1, "totalPages": 1},
                },
            },
        )
        mock_session = MagicMock()
        mock_session.get.return_value = mock_response

        with patch(
            "posts.integrations.sayra_client.get_http_session",
            return_value=mock_session,
        ):
            first = get_centers_by_ids(["gc-cached"])
            second = get_centers_by_ids(["gc-cached"])

            self.assertEqual(first["source"], "live")
            self.assertEqual(second["source"], "cache")
            self.assertEqual(mock_session.get.call_count, 1)

            # Bump version -> fresh cache misses, simulate Express timeout -> stale fallback serves cached data
            bump_sayra_cache_version()
            mock_session.get.side_effect = requests.Timeout("Express timed out")

            fallback = get_centers_by_ids(["gc-cached"])
            self.assertEqual(fallback["source"], "stale_cache")
            self.assertTrue(fallback["is_stale"])
            self.assertEqual(len(fallback["items"]), 1)
            self.assertEqual(fallback["items"][0]["id"], "gc-cached")

    @override_settings(NEXT_REVALIDATE_URL="http://nextjs:3000/api/revalidate")
    def test_webhook_verifies_hmac_invalidates_caches_and_triggers_revalidation(self):
        pub_time = timezone.now() - timedelta(minutes=5)
        article_tabriz = Article.objects.create(
            author=self.author,
            category=self.category,
            status="published",
            published_at=pub_time,
            gaming_center_mode="auto_ranking",
            ranking_city="تبریز",
        )
        ArticleTranslation.objects.create(
            article=article_tabriz,
            language_code="fa",
            slug="best-gaming-centers-tabriz",
            title="بهترین گیم‌نت‌های تبریز",
            excerpt="خلاصه",
        )
        article_manual = Article.objects.create(
            author=self.author,
            category=self.category,
            status="published",
            published_at=pub_time,
            gaming_center_mode="manual",
        )
        ArticleTranslation.objects.create(
            article=article_manual,
            language_code="fa",
            slug="manual-tabriz-guide",
            title="راهنمای تبریز",
            excerpt="خلاصه",
        )
        ArticleGamingCenter.objects.create(
            article=article_manual,
            gaming_center_id="center_01",
            display_order=0,
        )

        # Warm article detail cache via public API GET before webhook
        client = APIClient()
        with patch(
            "posts.integrations.sayra_client.get_rankings",
            return_value={
                "ranked": [],
                "newly_registered": [],
                "methodology": None,
                "source": "live",
                "is_stale": False,
                "fetched_at": None,
            },
        ), patch(
            "posts.integrations.sayra_client.get_centers_by_ids",
            return_value={"items": [], "source": "live", "is_stale": False, "fetched_at": None},
        ):
            res_before = client.get("/api/articles/slug/best-gaming-centers-tabriz/?lang=fa")
            self.assertEqual(res_before.status_code, 200)

        payload = {
            "eventId": "evt-100",
            "outboxEventId": "outbox-100",
            "eventType": "GAMING_CENTER_REVIEW_CHANGED",
            "gamingCenterId": "center_01",
            "gamingCenterSlug": "phoenix-esports-club",
            "city": "تبریز",
        }
        raw_body = json.dumps(payload)

        # 1. Invalid signature -> 401
        bad_res = client.post(
            "/api/integrations/webhooks/sayra-events/",
            data=raw_body,
            content_type="application/json",
            HTTP_X_SAYRA_TIMESTAMP=str(int(time.time())),
            HTTP_X_SAYRA_SIGNATURE="sha256=deadbeef",
        )
        self.assertEqual(bad_res.status_code, 401)

        # 2. Stale timestamp -> 401
        stale_ts = int(time.time()) - 900
        stale_sig = hmac.new(
            b"test-webhook-secret",
            f"{stale_ts}.{raw_body}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        stale_res = client.post(
            "/api/integrations/webhooks/sayra-events/",
            data=raw_body,
            content_type="application/json",
            HTTP_X_SAYRA_TIMESTAMP=str(stale_ts),
            HTTP_X_SAYRA_SIGNATURE=f"sha256={stale_sig}",
        )
        self.assertEqual(stale_res.status_code, 401)

        # 3. Valid signature -> 200 + cache invalidation + revalidation dispatch
        ts = int(time.time())
        sig = hmac.new(
            b"test-webhook-secret",
            f"{ts}.{raw_body}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        with patch("posts.integrations.webhook_views.trigger_frontend_revalidation_task.delay") as mock_delay:
            ok_res = client.post(
                "/api/integrations/webhooks/sayra-events/",
                data=raw_body,
                content_type="application/json",
                HTTP_X_SAYRA_EVENT_ID="outbox-100",
                HTTP_X_SAYRA_TIMESTAMP=str(ts),
                HTTP_X_SAYRA_SIGNATURE=f"sha256={sig}",
            )

        self.assertEqual(ok_res.status_code, 200)
        envelope = ok_res.json()
        body_data = envelope.get("data", envelope)
        self.assertTrue(body_data["accepted"])
        self.assertFalse(body_data["duplicate"])
        self.assertEqual(body_data["affected_articles"], 2)
        self.assertIn("/blog/best-gaming-centers-tabriz", body_data["revalidated_paths"])
        self.assertIn("/blog/manual-tabriz-guide", body_data["revalidated_paths"])
        self.assertIn("/gamecenter/phoenix-esports-club", body_data["revalidated_paths"])
        self.assertEqual(mock_delay.call_count, 1)

        # 4. Duplicate event ID -> idempotent 200 with duplicate=True
        with patch("posts.integrations.webhook_views.trigger_frontend_revalidation_task.delay") as mock_delay_dup:
            dup_res = client.post(
                "/api/integrations/webhooks/sayra-events/",
                data=raw_body,
                content_type="application/json",
                HTTP_X_SAYRA_EVENT_ID="outbox-100",
                HTTP_X_SAYRA_TIMESTAMP=str(ts),
                HTTP_X_SAYRA_SIGNATURE=f"sha256={sig}",
            )
        self.assertEqual(dup_res.status_code, 200)
        dup_data = dup_res.json().get("data", dup_res.json())
        self.assertTrue(dup_data["duplicate"])
        self.assertEqual(mock_delay_dup.call_count, 0)

    def test_article_create_update_serializer_syncs_gaming_center_links(self):
        serializer = ArticleCreateUpdateSerializer(
            data={
                "language_code": "fa",
                "title": "مقایسه گیم‌نت‌ها",
                "slug": "compare-gamecenters",
                "excerpt": "چکیده مقایسه",
                "status": "draft",
                "gaming_center_mode": "manual",
                "gaming_center_links": [
                    {
                        "gaming_center_id": "center_03",
                        "display_order": 0,
                        "custom_description": "بهترین سیستم PC",
                    },
                    {
                        "gaming_center_id": "center_05",
                        "display_order": 1,
                        "custom_description": "سالن PS5 اختصاصی",
                    },
                ],
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        article = serializer.save(author=self.author)

        links = list(article.gaming_center_links.all())
        self.assertEqual(
            [(l.gaming_center_id, l.display_order, l.custom_description) for l in links],
            [
                ("center_03", 0, "بهترین سیستم PC"),
                ("center_05", 1, "سالن PS5 اختصاصی"),
            ],
        )

        # Update links + reject duplicate IDs
        bad_update = ArticleCreateUpdateSerializer(
            article,
            data={
                "gaming_center_links": [
                    {"gaming_center_id": "center_03", "display_order": 0},
                    {"gaming_center_id": "center_03", "display_order": 1},
                ]
            },
            partial=True,
        )
        self.assertFalse(bad_update.is_valid())
        self.assertIn("gaming_center_links", bad_update.errors)

    def test_seed_tabriz_sample_article_command_creates_draft_idempotently(self):
        call_command("seed_tabriz_sample_article")
        call_command("seed_tabriz_sample_article")

        translations = ArticleTranslation.objects.filter(
            slug="best-gaming-centers-tabriz", language_code="fa"
        )
        self.assertEqual(translations.count(), 1)
        article = translations.first().article
        self.assertEqual(article.status, "draft")
        self.assertEqual(article.gaming_center_mode, "auto_ranking")
        self.assertEqual(article.ranking_city, "تبریز")
        self.assertEqual(article.ranking_min_reviews, 3)
        self.assertEqual(article.ranking_bayesian_m, 3.0)
        self.assertTrue(article.include_newly_registered)
