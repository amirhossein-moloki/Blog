"""
EN: Dedicated Celery tasks for asynchronous, multi-container safe cache warmup.
FA: تسک‌های اختصاصی Celery برای پیش‌گرم کردن غیرهمزمان و ایمن کش در محیط‌های چندکانتینری.
"""

import logging
import time

from celery import shared_task
from django.utils import timezone

from common.cache import build_cache_key, cache_manager, metrics_tracker

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    time_limit=120,
    soft_time_limit=110,
)
def warmup_homepage(self):
    """
    EN: Asynchronously warms up the homepage and categories lists caches.
    FA: پیش‌گرم کردن کش‌های لیست صفحه اصلی و دسته‌بندی‌ها به صورت ناهمزمان.
    """
    start_time = time.time()
    lock_key = "lock:warmup:homepage"
    success, token = cache_manager.try_acquire_lock(
        lock_key, expire_sec=60, timeout_sec=0
    )
    if not success:
        logger.info(
            "Warmup homepage task already running. Skipping duplicate execution."
        )
        return

    try:
        from posts.models import Article, Category
        from posts.serializers import ArticleListSerializer, CategorySerializer

        logger.info("Starting background homepage warmup task...")

        # Rebuild Homepage for English
        articles_en = (
            Article.objects.with_translations("en")
            .filter(status="published")
            .order_by("-published_at", "-id")[:10]
        )
        serializer_en = ArticleListSerializer(articles_en, many=True)
        homepage_key_en = build_cache_key(
            "posts",
            "article_list",
            "list",
            params={"page": "1", "pagesize": "10"},
            lang="en",
        )
        cache_manager.set(
            key=homepage_key_en,
            value={
                "data": serializer_en.data,
                "pagination": {
                    "pageNo": 1,
                    "pageSize": 10,
                    "totalPage": 1,
                    "totalCount": len(articles_en),
                    "lastId": None,
                },
                "messagesList": [],
            },
            group="homepage",
            soft_ttl_sec=300,
            hard_ttl_sec=900,
        )

        # Rebuild Homepage for Persian
        articles_fa = (
            Article.objects.with_translations("fa")
            .filter(status="published")
            .order_by("-published_at", "-id")[:10]
        )
        serializer_fa = ArticleListSerializer(articles_fa, many=True)
        homepage_key_fa = build_cache_key(
            "posts",
            "article_list",
            "list",
            params={"page": "1", "pagesize": "10"},
            lang="fa",
        )
        cache_manager.set(
            key=homepage_key_fa,
            value={
                "data": serializer_fa.data,
                "pagination": {
                    "pageNo": 1,
                    "pageSize": 10,
                    "totalPage": 1,
                    "totalCount": len(articles_fa),
                    "lastId": None,
                },
                "messagesList": [],
            },
            group="homepage",
            soft_ttl_sec=300,
            hard_ttl_sec=900,
        )

        # Rebuild Categories list
        cats = Category.objects.select_related("parent").all()
        categories_key = build_cache_key("posts", "category_list", "list")
        cache_manager.set(
            key=categories_key,
            value=CategorySerializer(cats, many=True).data,
            group="categories",
            soft_ttl_sec=86400,
            hard_ttl_sec=604800,
        )

        duration = time.time() - start_time
        metrics_tracker.record_celery_execution(duration)
        metrics_tracker.record_warmup_success(duration)
        logger.info(
            f"Homepage warmup completed successfully in {duration:.4f} seconds."
        )

    except Exception as e:
        metrics_tracker.record_warmup_failure()
        logger.error(f"Failed to execute warmup_homepage: {e}", exc_info=True)
        try:
            countdown = 5 * (2**self.request.retries)
            raise self.retry(exc=e, countdown=countdown)
        except self.MaxRetriesExceededError:
            logger.error("Max retries exceeded for warmup_homepage")
            raise e
    finally:
        if token:
            cache_manager.release_lock(lock_key, token)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    time_limit=120,
    soft_time_limit=110,
)
def warmup_article_detail(self, article_slug):
    """
    EN: Asynchronously warms up the article detail page cache.
    FA: پیش‌گرم کردن کش صفحه جزئیات مقاله به صورت ناهمزمان.
    """
    start_time = time.time()
    lock_key = f"lock:warmup:article_detail:{article_slug}"
    success, token = cache_manager.try_acquire_lock(
        lock_key, expire_sec=60, timeout_sec=0
    )
    if not success:
        logger.info(
            f"Warmup article detail task for {article_slug} already running. Skipping duplicate execution."
        )
        return

    try:
        from posts.models import Article
        from posts.serializers import ArticleDetailSerializer

        logger.info(
            f"Starting background article detail warmup task for {article_slug}..."
        )

        # Find the article by slug across all translations
        article = (
            Article.objects.filter(translations__slug=article_slug).distinct().first()
        )
        if not article:
            logger.warning(f"Article not found for warmup: {article_slug}")
            return

        # Build for each available language code in translations
        for lang in ["en", "fa"]:
            cache_key = build_cache_key(
                "posts",
                "article_detail",
                article_slug,
                params={"lang": lang},
                lang=lang,
            )
            # Fetch with translations prefetch
            obj_localized = (
                Article.objects.with_translations(lang).filter(pk=article.pk).first()
            )
            if obj_localized:
                serializer = ArticleDetailSerializer(obj_localized)
                cache_manager.set(
                    key=cache_key,
                    value=serializer.data,
                    group="article_detail",
                    tags=[f"article_detail:{article_slug}"],
                    soft_ttl_sec=600,
                    hard_ttl_sec=1800,
                )

        duration = time.time() - start_time
        metrics_tracker.record_celery_execution(duration)
        metrics_tracker.record_warmup_success(duration)
        logger.info(
            f"Article detail warmup for {article_slug} completed in {duration:.4f} seconds."
        )

    except Exception as e:
        metrics_tracker.record_warmup_failure()
        logger.error(f"Failed to execute warmup_article_detail: {e}", exc_info=True)
        try:
            countdown = 5 * (2**self.request.retries)
            raise self.retry(exc=e, countdown=countdown)
        except self.MaxRetriesExceededError:
            logger.error(
                f"Max retries exceeded for warmup_article_detail on {article_slug}"
            )
            raise e
    finally:
        if token:
            cache_manager.release_lock(lock_key, token)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    time_limit=120,
    soft_time_limit=110,
)
def warmup_category_pages(self, category_slug):
    """
    EN: Asynchronously warms up the category details cache.
    FA: پیش‌گرم کردن کش جزئیات دسته‌بندی به صورت ناهمزمان.
    """
    start_time = time.time()
    lock_key = f"lock:warmup:category:{category_slug}"
    success, token = cache_manager.try_acquire_lock(
        lock_key, expire_sec=60, timeout_sec=0
    )
    if not success:
        logger.info(
            f"Warmup category pages task for {category_slug} already running. Skipping duplicate execution."
        )
        return

    try:
        from posts.models import Category
        from posts.serializers import CategorySerializer

        logger.info(
            f"Starting background category pages warmup task for {category_slug}..."
        )

        category = Category.objects.filter(slug=category_slug).first()
        if category:
            cache_key = build_cache_key("posts", "category_detail", category_slug)
            serializer = CategorySerializer(category)
            cache_manager.set(
                key=cache_key,
                value=serializer.data,
                group="categories",
                tags=[f"category_detail:{category_slug}"],
                soft_ttl_sec=3600,
                hard_ttl_sec=7200,
            )

        duration = time.time() - start_time
        metrics_tracker.record_celery_execution(duration)
        metrics_tracker.record_warmup_success(duration)
        logger.info(
            f"Category pages warmup for {category_slug} completed in {duration:.4f} seconds."
        )

    except Exception as e:
        metrics_tracker.record_warmup_failure()
        logger.error(f"Failed to execute warmup_category_pages: {e}", exc_info=True)
        try:
            countdown = 5 * (2**self.request.retries)
            raise self.retry(exc=e, countdown=countdown)
        except self.MaxRetriesExceededError:
            logger.error(
                f"Max retries exceeded for warmup_category_pages on {category_slug}"
            )
            raise e
    finally:
        if token:
            cache_manager.release_lock(lock_key, token)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    time_limit=120,
    soft_time_limit=110,
)
def warmup_related_content(self, article_slug):
    """
    EN: Asynchronously warms up related articles caches.
    FA: پیش‌گرم کردن کش‌های مقالات مرتبط به صورت ناهمزمان.
    """
    start_time = time.time()
    lock_key = f"lock:warmup:related:{article_slug}"
    success, token = cache_manager.try_acquire_lock(
        lock_key, expire_sec=60, timeout_sec=0
    )
    if not success:
        logger.info(
            f"Warmup related content task for {article_slug} already running. Skipping duplicate execution."
        )
        return

    try:
        from django.db.models import Count, Q

        from posts.models import Article
        from posts.serializers import ArticleListSerializer

        logger.info(
            f"Starting background related content warmup task for {article_slug}..."
        )

        current_article = (
            Article.objects.filter(translations__slug=article_slug).distinct().first()
        )
        if not current_article:
            logger.warning(f"Article not found for related warmup: {article_slug}")
            return

        tag_ids = current_article.tags.values_list("id", flat=True)
        if not tag_ids:
            related = []
        else:
            related_qs = (
                Article.objects.filter(status="published", tags__in=tag_ids)
                .exclude(pk=current_article.pk)
                .distinct()
            )
            related_qs = related_qs.annotate(
                common_tags=Count("tags", filter=Q(tags__in=tag_ids))
            ).order_by("-common_tags", "-published_at", "-id")[:10]
            serializer = ArticleListSerializer(related_qs, many=True)
            related = serializer.data

        cache_key = build_cache_key("posts", "related_articles", article_slug)
        cache_manager.set(
            key=cache_key,
            value=related,
            group="article_detail",
            tags=[f"article_detail:{article_slug}"],
            soft_ttl_sec=600,
            hard_ttl_sec=1800,
        )

        duration = time.time() - start_time
        metrics_tracker.record_celery_execution(duration)
        metrics_tracker.record_warmup_success(duration)
        logger.info(
            f"Related content warmup for {article_slug} completed in {duration:.4f} seconds."
        )

    except Exception as e:
        metrics_tracker.record_warmup_failure()
        logger.error(f"Failed to execute warmup_related_content: {e}", exc_info=True)
        try:
            countdown = 5 * (2**self.request.retries)
            raise self.retry(exc=e, countdown=countdown)
        except self.MaxRetriesExceededError:
            logger.error(
                f"Max retries exceeded for warmup_related_content on {article_slug}"
            )
            raise e
    finally:
        if token:
            cache_manager.release_lock(lock_key, token)
