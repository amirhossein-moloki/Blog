from datetime import timedelta
from unittest import mock

import dj_database_url
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from common.cache import cache_manager
from common.cache.serializers import JSONSerializer
from posts.blog_tests.base import BaseAPITestCase
from posts.factories import (
    ArticleFactory,
    CategoryFactory,
    CommentFactory,
    MediaFactory,
    ReactionFactory,
    TagFactory,
    UserFactory,
)
from posts.models import Article, ArticleTranslation, Series
from posts.services import (
    ARTICLE_VIEW_BUFFER_HASH,
    ARTICLE_VIEW_FALLBACK_IDS_KEY,
    flush_buffered_article_view_counts,
)


class Wave3BlogPerformanceTestCase(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.list_url = reverse("posts:article-list")

    def test_distinct_comment_and_reaction_counts_prevent_cartesian_multiplication(self):
        article = ArticleFactory(author=self.author_profile, status="published")
        for _ in range(3):
            CommentFactory(article=article, user=UserFactory(), status="approved")
        CommentFactory(article=article, user=UserFactory(), status="spam")
        for _ in range(4):
            ReactionFactory(content_object=article, user=UserFactory(), reaction="like")

        fetched = Article.objects.get(pk=article.pk)
        self.assertEqual(fetched.comments_count, 3)
        self.assertEqual(fetched.likes_count, 4)

    def test_article_list_cache_isolates_staff_drafts_and_ignores_garbage_params(self):
        ArticleFactory(
            author=self.author_profile,
            status="published",
            published_at=timezone.now() - timedelta(hours=1),
            translation__title="Public Post",
            translation__slug="public-post-w3",
        )
        ArticleFactory(
            author=self.author_profile,
            status="draft",
            translation__title="Secret Staff Draft",
            translation__slug="secret-staff-draft-w3",
        )

        # 1. Staff fetches list (must bypass public cache)
        self._authenticate_as_staff()
        staff_res = self.client.get(self.list_url)
        self.assertEqual(staff_res.status_code, status.HTTP_200_OK)
        self.assertIn("private", staff_res["Cache-Control"])
        self.assertEqual(len(staff_res.data["data"]), 2)

        # 2. Anonymous fetches list -> must only see 1 published post
        self.client.credentials()
        anon_res1 = self.client.get(f"{self.list_url}?page=1&utm_source=abc&rand=1")
        self.assertEqual(anon_res1.status_code, status.HTTP_200_OK)
        self.assertEqual(len(anon_res1.data["data"]), 1)
        self.assertEqual(anon_res1.data["data"][0]["slug"], "public-post-w3")
        self.assertIn("public", anon_res1["Cache-Control"])

        # 3. Different unknown garbage params hit same cache key without DB hit
        with self.assertNumQueries(0):
            anon_res2 = self.client.get(
                f"{self.list_url}?page=1&utm_source=different&fbclid=999"
            )
        self.assertEqual(anon_res2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(anon_res2.data["data"]), 1)

    def test_article_retrieve_cache_hit_executes_zero_sql_and_buffers_views(self):
        article = ArticleFactory(
            author=self.author_profile,
            status="published",
            published_at=timezone.now() - timedelta(hours=1),
            views_count=10,
            translation__slug="cached-detail-w3",
        )
        url = reverse("posts:article-detail", kwargs={"slug": "cached-detail-w3"})

        self.client.credentials()
        res_cold = self.client.get(url)
        self.assertEqual(res_cold.status_code, status.HTTP_200_OK)

        with self.assertNumQueries(0):
            res_warm1 = self.client.get(url)
            res_warm2 = self.client.get(url)
        self.assertEqual(res_warm1.status_code, status.HTTP_200_OK)
        self.assertEqual(res_warm2.status_code, status.HTTP_200_OK)

        # All 3 GETs were buffered cleanly without DB writes until flush runs
        article.refresh_from_db()
        self.assertEqual(article.views_count, 10)

        flushed = flush_buffered_article_view_counts()
        self.assertEqual(flushed, 3)
        article.refresh_from_db()
        self.assertEqual(article.views_count, 13)
        self.assertIsNone(cache.get(ARTICLE_VIEW_FALLBACK_IDS_KEY))
        self.assertIsNone(cache.get(f"{ARTICLE_VIEW_BUFFER_HASH}:{article.pk}"))

    def test_similar_and_same_category_run_constant_queries_independent_of_article_count(self):
        category = CategoryFactory()
        tag = TagFactory()
        target = ArticleFactory(
            author=self.author_profile,
            category=category,
            cover_image=MediaFactory(),
            status="published",
            published_at=timezone.now() - timedelta(days=1),
            translation__slug="target-related-w3",
        )
        target.tags.add(tag)

        for idx in range(2):
            art = ArticleFactory(
                author=self.author_profile,
                category=category,
                cover_image=MediaFactory(),
                status="published",
                published_at=timezone.now() - timedelta(days=idx + 2),
                translation__slug=f"related-small-{idx}-w3",
            )
            art.tags.add(tag)

        similar_url = reverse(
            "posts:article-similar", kwargs={"slug": "target-related-w3"}
        )
        same_cat_url = reverse(
            "posts:article-same-category", kwargs={"slug": "target-related-w3"}
        )

        self.client.credentials()
        cache.clear()
        with CaptureQueriesContext(connection) as ctx_sim_2:
            r1 = self.client.get(similar_url)
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        sim_2_items = r1.data["data"] if isinstance(r1.data, dict) else r1.data
        self.assertEqual(len(sim_2_items), 2)

        cache.clear()
        with CaptureQueriesContext(connection) as ctx_cat_2:
            r2 = self.client.get(same_cat_url)
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r2.data["data"]), 2)

        # Add 3 more articles in same category -> query count must stay O(1) equal
        for idx in range(3):
            art = ArticleFactory(
                author=self.author_profile,
                category=category,
                cover_image=MediaFactory(),
                status="published",
                published_at=timezone.now() - timedelta(days=idx + 10),
                translation__slug=f"related-more-{idx}-w3",
            )
            art.tags.add(tag)

        cache.clear()
        with self.assertNumQueries(len(ctx_sim_2)):
            r3 = self.client.get(similar_url)
        self.assertEqual(r3.status_code, status.HTTP_200_OK)
        sim_5_items = r3.data["data"] if isinstance(r3.data, dict) else r3.data
        self.assertEqual(len(sim_5_items), 5)

        cache.clear()
        with self.assertNumQueries(len(ctx_cat_2)):
            r4 = self.client.get(same_cat_url)
        self.assertEqual(r4.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r4.data["data"]), 5)

    def test_cache_manager_avoids_ping_batches_versions_and_shrinks_envelope(self):
        fake_redis = mock.MagicMock()
        orig_client = cache_manager._redis_client
        orig_available = cache_manager._is_redis_available
        try:
            cache_manager._redis_client = fake_redis
            cache_manager._is_redis_available = True

            self.assertIs(cache_manager._get_raw_client(), fake_redis)
            fake_redis.ping.assert_not_called()
        finally:
            cache_manager._redis_client = orig_client
            cache_manager._is_redis_available = orig_available

        # Batch version lookup uses get_many
        with mock.patch.object(
            cache_manager.invalidation.cache_client,
            "get_many",
            wraps=cache_manager.invalidation.cache_client.get_many,
        ) as get_many_spy:
            ok = cache_manager.set(
                "w3:batch:test",
                {"hello": "world", "items": list(range(100))},
                group="latest_articles",
                tags=["t1", "t2", "t3"],
                soft_ttl_sec=60,
                hard_ttl_sec=120,
            )
            self.assertTrue(ok)
            self.assertEqual(cache_manager.get("w3:batch:test")["hello"], "world")
            self.assertEqual(get_many_spy.call_count, 2)

        # JSONSerializer + base64 shrinks envelope size vs legacy 2x hex encoding
        json_mgr = cache_manager.__class__(
            serializer=JSONSerializer(),
            compression_threshold_bytes=64,
        )
        sample_payload = {"items": ["x" * 50 for _ in range(30)]}
        packed = json_mgr._pack_envelope(sample_payload)
        self.assertIsNotNone(packed)
        serialized_raw = json_mgr.compressor.compress(
            json_mgr.serializer.serialize(sample_payload)
        )
        legacy_hex_size = len(serialized_raw.hex())
        self.assertLess(len(packed), legacy_hex_size + 120)

        # Backward compatibility: legacy hex_encoded envelope unpacks cleanly
        legacy_env = json_mgr.serializer.serialize(
            {
                "p": serialized_raw.hex(),
                "c": True,
                "hex_encoded": True,
                "g": None,
                "gv": 1,
                "t": [],
                "tv": {},
                "st": 9999999999.0,
                "ht": 9999999999.0,
            }
        )
        unpacked, is_stale = json_mgr._unpack_envelope(legacy_env)
        self.assertFalse(is_stale)
        self.assertEqual(unpacked, sample_payload)

    def test_dj_database_url_pooling_helper_config(self):
        cfg = dj_database_url.config(
            default="postgres://u:p@localhost:5432/db",
            conn_max_age=60,
            conn_health_checks=True,
        )
        self.assertEqual(cfg["CONN_MAX_AGE"], 60)
        self.assertTrue(cfg["CONN_HEALTH_CHECKS"])

    def test_seo_phase2_to_4_and_wave3_integration(self):
        # 1. Series.get_absolute_url resolves series-detail (SEO Phase 3, pk-based DRF route)
        series = Series.objects.create(title="SEO Series", slug="seo-series-w3")
        self.assertEqual(
            series.get_absolute_url(),
            reverse("posts:series-detail", kwargs={"pk": series.pk}),
        )

        # 2. Article with both 'fa' and 'en' defaults to 'fa' and exposes ISO timestamps
        dual_article = ArticleFactory(
            author=self.author_profile,
            status="published",
            published_at=timezone.now() - timedelta(hours=2),
            translation__language_code="en",
            translation__title="English Title",
            translation__slug="dual-article-en-w3",
        )
        ArticleTranslation.objects.create(
            article=dual_article,
            language_code="fa",
            title="عنوان فارسی",
            slug="dual-article-fa-w3",
            excerpt="خلاصه فارسی",
            content="محتوای تست",
        )

        # 3. English-only articles still work when default lang='fa' without N+1 queries
        en_only_articles = [
            ArticleFactory(
                author=self.author_profile,
                status="published",
                published_at=timezone.now() - timedelta(hours=3 + idx),
                translation__language_code="en",
                translation__title=f"English Only {idx}",
                translation__slug=f"en-only-w3-{idx}",
            )
            for idx in range(2)
        ]

        self.client.credentials()
        cache.clear()
        with CaptureQueriesContext(connection) as ctx_list:
            res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        items_by_slug = {item["slug"]: item for item in res.data["data"]}
        self.assertIn("dual-article-fa-w3", items_by_slug)
        self.assertEqual(items_by_slug["dual-article-fa-w3"]["title"], "عنوان فارسی")
        self.assertIn("published_at_iso", items_by_slug["dual-article-fa-w3"])
        self.assertIn("updated_at_iso", items_by_slug["dual-article-fa-w3"])
        self.assertIn("en-only-w3-0", items_by_slug)
        self.assertIn("en-only-w3-1", items_by_slug)

        # Check prefetched model query count stays O(1) for both fa and en-only articles
        qs_count_before = len(ctx_list)
        self.assertLessEqual(qs_count_before, 15)
        with self.assertNumQueries(4):
            fetched = list(
                Article.objects.with_translations("fa").filter(
                    pk__in=[dual_article.pk, *[a.pk for a in en_only_articles]]
                )
            )
        with self.assertNumQueries(0):
            resolved_slugs = {a.pk: a.translation.slug for a in fetched}
        self.assertEqual(resolved_slugs[dual_article.pk], "dual-article-fa-w3")
        self.assertEqual(resolved_slugs[en_only_articles[0].pk], "en-only-w3-0")
