from django.db.models import Count, F, Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response

from common.cache import build_cache_key, cache_manager
from common.filters import NormalizedSearchFilter
from common.mixins import DynamicSerializerViewMixin
from common.pagination import CustomPageNumberPagination
from common.permissions import (
    IsAdminUserOrReadOnly,
    IsArticleAuthorOrAdmin,
    IsAuthorProfileOwnerOrAdmin,
)
from interactions.models import Comment
from interactions.serializers import CommentListSerializer
from medias.models import Media
from users.permissions import IsAdminUser, IsOwnerOrAdmin

from .filters import ArticleFilter
from .models import (
    Article,
    AuthorProfile,
    Category,
    GalleryItem,
    Podcast,
    PodcastCategory,
    Revision,
    Series,
    Tag,
)
from .serializers import (
    ArticleCreateUpdateSerializer,
    ArticleDetailSerializer,
    ArticleListSerializer,
    AuthorProfileSerializer,
    CategorySerializer,
    GalleryItemSerializer,
    PodcastCategorySerializer,
    PodcastSerializer,
    RevisionSerializer,
    SeriesSerializer,
    TagSerializer,
)
from .services import buffer_article_view_count

ARTICLE_LIST_CACHE_PARAMS = (
    "page",
    "page_size",
    "pageNo",
    "pageSize",
    "status",
    "category",
    "tags",
    "series",
    "visibility",
    "published_after",
    "published_before",
    "is_hot",
    "search",
    "ordering",
    "lang",
    "fields",
)


def _extract_allowlisted_cache_params(query_params, allowed_keys):
    params = {}
    for key in allowed_keys:
        values = query_params.getlist(key)
        if values:
            params[key] = values[0] if len(values) == 1 else sorted(values)
    return params


def _is_staff_user(user) -> bool:
    return bool(
        user
        and getattr(user, "is_authenticated", False)
        and getattr(user, "is_staff", False)
    )


def _set_public_cache_headers(
    request,
    response,
    max_age: int = 120,
    s_maxage: int = 300,
    swr: int = 600,
):
    """
    EN: Adds CDN/browser caching headers only for unauthenticated read responses.
    FA: هدرهای کش را فقط برای درخواست‌های عمومی بدون احراز هویت تنظیم می‌کند.
    """
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        response["Cache-Control"] = "private, no-cache"
    else:
        response["Cache-Control"] = (
            f"public, max-age={max_age}, s-maxage={s_maxage}, stale-while-revalidate={swr}"
        )
    return response


class ArticleViewSet(DynamicSerializerViewMixin, viewsets.ModelViewSet):
    """
    EN:
    ViewSet for managing blog articles.
    Provides advanced filtering, searching, and dynamic field selection.
    Handles complex queryset optimizations and access control for drafts/scheduled articles.

    FA:
    ViewSet برای مدیریت مقاله‌های بلاگ.
    فیلترینگ پیشرفته، جستجو و انتخاب داینامیک فیلدها را فراهم می‌کند.
    بهینه‌سازی‌های پیچیده QuerySet و کنترل دسترسی برای پیش‌نویس‌ها و مقاله‌های زمان‌بندی شده را مدیریت می‌کند.
    """

    queryset = Article.objects.all()
    permission_classes = [IsArticleAuthorOrAdmin]
    pagination_class = CustomPageNumberPagination
    filter_backends = [DjangoFilterBackend, NormalizedSearchFilter, OrderingFilter]
    filterset_class = ArticleFilter
    search_fields = [
        "translations__title",
        "translations__content",
        "translations__excerpt",
    ]
    ordering_fields = ["published_at", "views_count", "id"]
    ordering = ["-published_at", "-id"]
    lookup_field = "translations__slug"
    lookup_url_kwarg = "slug"

    def get_serializer_class(self):
        """
        EN: Returns the serializer class based on the action.
        FA: کلاس سریالایزر را بر اساس اکشن بازمی‌گرداند.
        """
        if self.action in ["create", "update", "partial_update"]:
            return ArticleCreateUpdateSerializer
        elif self.action == "retrieve":
            return ArticleDetailSerializer
        return ArticleListSerializer

    def list(self, request, *args, **kwargs):
        """
        EN: Lists articles with advanced caching (strictly public-scoped) and fallback.
        FA: مقاله‌ها را با قابلیت کشینگ امن (تفکیک‌شده برای کاربران عادی و احرازهویت‌شده) لیست می‌کند.
        """
        is_authenticated = bool(
            getattr(request, "user", None) and request.user.is_authenticated
        )

        def build_response_data():
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data).data
            serializer = self.get_serializer(queryset, many=True)
            return serializer.data

        if is_authenticated:
            return _set_public_cache_headers(request, Response(build_response_data()))

        lang = request.query_params.get("lang", "fa")
        params = _extract_allowlisted_cache_params(
            request.query_params, ARTICLE_LIST_CACHE_PARAMS
        )
        cache_key = build_cache_key(
            "posts", "article_list", "list_public", params=params, lang=lang
        )

        data = cache_manager.get_or_create(
            key=cache_key,
            rebuild_callback=build_response_data,
            group="latest_articles",
            soft_ttl_sec=300,
            hard_ttl_sec=900,
        )
        return _set_public_cache_headers(request, Response(data), 120, 300, 600)

    def get_queryset(self):
        """
        EN:
        Optimizes the queryset using select_related and prefetch_related based on requested fields.
        Also handles visibility rules and localization.

        FA:
        QuerySet را با استفاده از select_related و prefetch_related بر اساس فیلدهای درخواستی بهینه می‌کند.
        همچنین قوانین مشاهده‌پذیری و بومی‌سازی را مدیریت می‌کند.
        """
        lang = self.request.query_params.get("lang", "fa")
        if self.action == "list":
            queryset = Article.objects.with_translations(lang)
            fields_query = self.request.query_params.get("fields")
            fields = (
                {f.strip() for f in fields_query.split(",")} if fields_query else set()
            )

            selects = set()
            prefetches = set()

            if not fields:
                fields = {
                    "slug",
                    "title",
                    "excerpt",
                    "author",
                    "category",
                    "cover_image",
                    "tags",
                    "likes_count",
                    "comments_count",
                }

            if "author" in fields:
                selects.add("author__avatar")
                prefetches.add("author__avatar__variants")
            if "category" in fields:
                selects.add("category")
            if "cover_image" in fields:
                selects.add("cover_image")
                prefetches.add("cover_image__variants")
            if "tags" in fields:
                prefetches.add("tags")
            if "likes_count" in fields:
                prefetches.add("reactions")

            if selects:
                queryset = queryset.select_related(*selects)
            if prefetches:
                queryset = queryset.prefetch_related(*prefetches)

            user = self.request.user
            if _is_staff_user(user):
                return queryset
            if user and user.is_authenticated:
                return queryset.filter(
                    Q(
                        status="published",
                        published_at__lte=timezone.now(),
                        visibility="public",
                    )
                    | Q(author__user=user)
                ).distinct()
            return queryset.filter(
                status="published",
                published_at__lte=timezone.now(),
                visibility="public",
            )
        else:
            queryset = Article.objects.with_translations(lang)
            fields_query = self.request.query_params.get("fields")
            fields = (
                {f.strip() for f in fields_query.split(",")}
                if fields_query
                else {"all"}
            )

            selects = set()
            prefetches = set()
            all_fields = "all" in fields

            if all_fields or "author" in fields:
                selects.add("author__avatar")
            if_all_fields_or_category = all_fields or "category" in fields
            if if_all_fields_or_category:
                selects.add("category")
            if all_fields or "cover_image" in fields:
                selects.add("cover_image")
            if all_fields or "series" in fields:
                selects.add("series")
            if all_fields or "og_image" in fields:
                selects.add("og_image")
            if all_fields or "tags" in fields:
                prefetches.add("tags")
            if all_fields or "likes_count" in fields:
                prefetches.add("reactions")
            if all_fields or "comments" in fields:
                prefetches.add("comments__user")
            if all_fields or "media_attachments" in fields:
                prefetches.add("media_attachments__media")
            if all_fields or "gaming_center_links" in fields or "gaming_centers_section" in fields:
                prefetches.add("gaming_center_links")

            if selects:
                queryset = queryset.select_related(*selects)
            if prefetches:
                queryset = queryset.prefetch_related(*prefetches)

            user = self.request.user
            if _is_staff_user(user):
                return queryset
            if user and user.is_authenticated:
                return queryset.filter(
                    Q(
                        status="published",
                        published_at__lte=timezone.now(),
                        visibility__in=["public", "unlisted"],
                    )
                    | Q(author__user=user)
                ).distinct()
            return queryset.filter(
                status="published",
                published_at__lte=timezone.now(),
                visibility__in=["public", "unlisted"],
            )

    def perform_create(self, serializer):
        """
        EN: Associates the article with the author profile of the current user.
        FA: مقاله را به پروفایل نویسندگی کاربر فعلی مرتبط می‌کند.
        """
        user = self.request.user
        if not user or not user.is_authenticated:
            raise PermissionDenied("You do not have permission to create an article.")

        if user.is_staff:
            display_name = (
                user.get_full_name().strip()
                if hasattr(user, "get_full_name")
                else ""
            ) or user.username
            author_profile, _ = AuthorProfile.objects.get_or_create(
                user=user,
                defaults={"display_name": display_name},
            )
        else:
            try:
                author_profile = AuthorProfile.objects.get(user=user)
            except AuthorProfile.DoesNotExist:
                raise PermissionDenied(
                    "You do not have permission to create an article."
                )
        serializer.save(author=author_profile)

    def get_object(self):
        is_write = (
            getattr(self.request, "method", None) in ("PUT", "PATCH", "DELETE")
            or self.action in ("update", "partial_update", "destroy")
        )
        queryset = (
            self.get_queryset() if is_write else self.filter_queryset(self.get_queryset())
        )
        slug = self.kwargs[self.lookup_url_kwarg]
        lang = self.request.query_params.get("lang")
        obj = None
        if lang:
            obj = (
                queryset.filter(
                    translations__slug=slug, translations__language_code=lang
                )
                .distinct()
                .first()
            )
        if obj is None:
            obj = queryset.filter(translations__slug=slug).distinct().first()
        if obj is None:
            raise NotFound("No article was found with this slug.")

        matched_trans = None
        if lang:
            matched_trans = obj.translations.filter(
                slug=slug, language_code=lang
            ).first()
        if matched_trans is None:
            matched_trans = obj.translations.filter(slug=slug).first()
        if matched_trans is not None:
            obj._matched_translation_lang = matched_trans.language_code
            if not lang or not getattr(obj, "requested_translation", None):
                obj.requested_translation = [matched_trans]

        self.check_object_permissions(self.request, obj)
        return obj

    def retrieve(self, request, *args, **kwargs):
        """
        EN: Serves cached article details and increments view count via an atomic SQL update
            (avoiding Article.save() / sync_article_media on GET reads).
        FA: جزئیات مقاله را از کش بازمی‌گرداند و شمارنده بازدید را به‌صورت اتمی و بدون اجرای save() به‌روزرسانی می‌کند.
        """
        lookup_slug = kwargs.get(
            self.lookup_url_kwarg or self.lookup_field
        ) or str(kwargs.get("pk", ""))
        lang = request.query_params.get("lang", "fa")
        is_authenticated = bool(
            getattr(request, "user", None) and request.user.is_authenticated
        )

        if is_authenticated:
            obj = self.get_object()
            buffer_article_view_count(obj.pk)
            serializer = self.get_serializer(obj)
            return _set_public_cache_headers(request, Response(serializer.data))

        cache_key = build_cache_key(
            "posts", "article_detail", lookup_slug, params={"lang": lang}, lang=lang
        )

        def rebuild():
            try:
                obj = self.get_object()
            except Exception:
                return {
                    "_negative_cache_": True,
                    "status_code": 404,
                    "detail": "No article was found with this slug.",
                }
            serializer = self.get_serializer(obj)
            return serializer.data

        data = cache_manager.get_or_create(
            key=cache_key,
            rebuild_callback=rebuild,
            group="article_detail",
            tags=[f"article_detail:{lookup_slug}"],
            soft_ttl_sec=600,
            hard_ttl_sec=1800,
        )

        if isinstance(data, dict) and data.get("_negative_cache_", False):
            raise NotFound(data.get("detail", "No article was found with this slug."))

        article_id = data.get("id") if isinstance(data, dict) else None
        if article_id:
            buffer_article_view_count(article_id)

        return _set_public_cache_headers(request, Response(data), 120, 300, 600)

    @action(detail=True, methods=["get"])
    def similar(self, request, slug=None):
        """
        EN: Returns similar articles based on the category with O(1) prefetched queries.
        FA: مقاله‌های مشابه را بر اساس دسته‌بندی با کوئری‌های پیش‌واکشی‌شده بهینه بازمی‌گرداند.
        """
        lang = request.query_params.get("lang", "fa")
        try:
            current_article = self.get_object()
        except Article.DoesNotExist:
            raise NotFound(
                "The requested article to find similar articles was not found."
            )

        if not current_article.category_id:
            return _set_public_cache_headers(request, Response([]), 120, 300, 600)

        def rebuild():
            similar_qs = (
                Article.objects.with_translations(lang)
                .filter(
                    status="published",
                    category_id=current_article.category_id,
                    published_at__lte=timezone.now(),
                )
                .exclude(pk=current_article.pk)
            )
            if not _is_staff_user(request.user):
                similar_qs = similar_qs.filter(visibility="public")
            similar_articles = (
                similar_qs.select_related("author__avatar", "category", "cover_image")
                .prefetch_related(
                    "tags", "cover_image__variants", "author__avatar__variants"
                )
                .order_by("-published_at", "-id")[:5]
            )
            serializer = ArticleListSerializer(
                similar_articles, many=True, context=self.get_serializer_context()
            )
            return serializer.data

        is_authenticated = bool(
            getattr(request, "user", None) and request.user.is_authenticated
        )
        if is_authenticated:
            return _set_public_cache_headers(request, Response(rebuild()))

        cache_key = build_cache_key(
            "posts",
            "article_similar",
            str(current_article.pk),
            params={"lang": lang, "category": current_article.category_id},
            lang=lang,
        )
        data = cache_manager.get_or_create(
            key=cache_key,
            rebuild_callback=rebuild,
            group="latest_articles",
            soft_ttl_sec=300,
            hard_ttl_sec=900,
        )
        return _set_public_cache_headers(request, Response(data), 120, 300, 600)

    @action(detail=True, methods=["get"], url_path="same-category")
    def same_category(self, request, slug=None):
        """
        EN: Returns paginated articles from the same category with O(1) prefetched queries.
        FA: مقاله‌های هم‌دسته‌بندی را به‌صورت صفحه‌بندی‌شده و بدون N+1 بازمی‌گرداند.
        """
        lang = request.query_params.get("lang", "fa")
        current_article = self.get_object()

        if not current_article.category_id:
            return Response(
                {
                    "data": [],
                    "pagination": {
                        "pageNo": 1,
                        "pageSize": 10,
                        "totalPage": 0,
                        "totalCount": 0,
                        "lastId": None,
                    },
                    "messagesList": [],
                }
            )

        paginator = self.pagination_class()

        def rebuild():
            category_qs = (
                Article.objects.with_translations(lang)
                .filter(
                    status="published",
                    category_id=current_article.category_id,
                    published_at__lte=timezone.now(),
                )
                .exclude(pk=current_article.pk)
            )
            if not _is_staff_user(request.user):
                category_qs = category_qs.filter(visibility="public")
            category_articles = (
                category_qs.select_related("author__avatar", "category", "cover_image")
                .prefetch_related(
                    "tags", "cover_image__variants", "author__avatar__variants"
                )
                .order_by("-published_at", "-id")
            )

            paginated_articles = paginator.paginate_queryset(
                category_articles, request, view=self
            )
            serializer = ArticleListSerializer(
                paginated_articles, many=True, context=self.get_serializer_context()
            )
            return paginator.get_paginated_response(serializer.data).data

        is_authenticated = bool(
            getattr(request, "user", None) and request.user.is_authenticated
        )
        if is_authenticated:
            return _set_public_cache_headers(request, Response(rebuild()))

        page_params = _extract_allowlisted_cache_params(
            request.query_params, ("page", "page_size", "pageNo", "pageSize", "lang")
        )
        cache_key = build_cache_key(
            "posts",
            "article_same_category",
            str(current_article.pk),
            params={"category": current_article.category_id, **page_params},
            lang=lang,
        )
        data = cache_manager.get_or_create(
            key=cache_key,
            rebuild_callback=rebuild,
            group="latest_articles",
            soft_ttl_sec=300,
            hard_ttl_sec=900,
        )
        return _set_public_cache_headers(request, Response(data), 120, 300, 600)

    @action(detail=False, methods=["get"], url_path="block-definitions")
    def block_definitions(self, request):
        """
        EN: Returns the complete content contract specifications list for headless components.
        """
        from posts.blocks import block_registry

        return Response(block_registry.get_all_definitions())

    @action(detail=False, methods=["get"], url_path="slug/(?P<slug>[^/.]+)")
    def by_slug(self, request, slug=None):
        """
        EN: Endpoint to retrieve a single article by its slug and language with advanced caching.
        FA: اندپوینت برای دریافت یک مقاله واحد با استفاده از اسلاگ و زبان آن به همراه کشینگ پیشرفته.
        """
        lang = request.query_params.get("lang", "fa")
        is_authenticated = bool(
            getattr(request, "user", None) and request.user.is_authenticated
        )

        def fetch_serialized():
            article = (
                self.get_queryset()
                .filter(translations__slug=slug, translations__language_code=lang)
                .first()
            )
            if not article:
                article = self.get_queryset().filter(translations__slug=slug).first()
            if not article:
                return None
            serializer = ArticleDetailSerializer(
                article, context=self.get_serializer_context()
            )
            return serializer.data

        if is_authenticated:
            payload = fetch_serialized()
            if payload is None:
                raise NotFound("No article was found with this slug.")
            return _set_public_cache_headers(request, Response(payload))
        cache_key = build_cache_key(
            "posts", "article_by_slug", slug, params={"lang": lang}, lang=lang
        )

        def rebuild():
            try:
                serialized = fetch_serialized()
                if serialized is not None:
                    return serialized
            except Exception:
                pass
            return {
                "_negative_cache_": True,
                "status_code": 404,
                "detail": "No article was found with this slug.",
            }

        data = cache_manager.get_or_create(
            key=cache_key,
            rebuild_callback=rebuild,
            group="article_detail",
            tags=[f"article_detail:{slug}"],
            soft_ttl_sec=600,
            hard_ttl_sec=1800,
        )

        if isinstance(data, dict) and data.get("_negative_cache_", False):
            raise NotFound(data.get("detail", "No article was found with this slug."))

        return _set_public_cache_headers(request, Response(data), 120, 300, 600)


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="article_slug",
            type=str,
            location=OpenApiParameter.PATH,
            description="The slug of the article to get comments for.",
        )
    ]
)
class ArticleCommentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    EN: ViewSet to list approved comments for a specific article.
    FA: ViewSet برای لیست کردن نظرات تایید شده برای یک مقاله خاص.
    """

    serializer_class = CommentListSerializer
    pagination_class = CustomPageNumberPagination
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [OrderingFilter]
    ordering_fields = ["created_at", "likes_count"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """
        EN: Returns approved comments for the specified article, annotated with likes.
        FA: نظرات تایید شده برای مقاله مشخص شده را به همراه تعداد لایک‌ها بازمی‌گرداند.
        """
        article_slug = self.kwargs.get("article_slug")
        return (
            Comment.objects.filter(
                article__translations__slug=article_slug, status="approved"
            )
            .annotate(
                likes_count=Count("reactions", filter=Q(reactions__reaction="like"))
            )
            .select_related("user__authorprofile")
        )


@extend_schema(
    request=None,
    responses={200: ArticleDetailSerializer},
    description="Publish a draft or scheduled article.",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated, IsOwnerOrAdmin])
def publish_article(request, slug):
    """
    EN: API view to manually publish a draft or scheduled article.
    FA: نمای API برای انتشار دستی یک مقاله پیش‌نویس یا زمان‌بندی شده.
    """
    article = Article.objects.filter(translations__slug=slug).distinct().first()
    if article is None:
        raise NotFound("No article was found with these specifications.")

    if article.author.user != request.user and not request.user.is_staff:
        raise PermissionDenied("You do not have permission to publish this article.")

    if article.status not in ["draft", "scheduled"]:
        return Response(
            {"detail": "Only draft or scheduled articles can be published."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    article.status = "published"
    article.published_at = timezone.now()
    article.scheduled_at = None
    article.save()
    serializer = ArticleDetailSerializer(article)
    return Response(serializer.data)


@extend_schema(
    responses={200: ArticleListSerializer(many=True)},
    description="Get related articles based on tags.",
)
@api_view(["GET"])
def related_articles(request, slug):
    """
    EN: Returns related articles sharing common tags with the specified article.
    FA: مقاله‌های مرتبط که دارای برچسب‌های مشترک با مقاله مشخص شده هستند را بازمی‌گرداند.
    """
    base_qs = Article.objects.all()
    if not _is_staff_user(request.user):
        if request.user and request.user.is_authenticated:
            base_qs = base_qs.filter(
                Q(
                    status="published",
                    published_at__lte=timezone.now(),
                    visibility__in=["public", "unlisted"],
                )
                | Q(author__user=request.user)
            ).distinct()
        else:
            base_qs = base_qs.filter(
                status="published",
                published_at__lte=timezone.now(),
                visibility__in=["public", "unlisted"],
            )

    current_article = base_qs.filter(translations__slug=slug).first()
    if not current_article:
        raise NotFound("The requested article to find related articles was not found.")

    paginator = CustomPageNumberPagination()
    tag_ids = current_article.tags.values_list("id", flat=True)

    if not tag_ids:
        related = Article.objects.none()
    else:
        related = (
            Article.objects.filter(
                status="published",
                published_at__lte=timezone.now(),
                tags__in=tag_ids,
            )
            .exclude(pk=current_article.pk)
        )
        if not _is_staff_user(request.user):
            related = related.filter(visibility="public")
        related = related.distinct()
        related = related.annotate(
            common_tags=Count("tags", filter=Q(tags__in=tag_ids))
        ).order_by("-common_tags", "-published_at", "-id")

    paginated_related_articles = paginator.paginate_queryset(related, request)
    serializer = ArticleListSerializer(
        paginated_related_articles, many=True, context={"request": request}
    )
    return paginator.get_paginated_response(serializer.data)


class AuthorProfileViewSet(viewsets.ModelViewSet):
    """
    EN: ViewSet for managing author profiles.
    FA: ViewSet برای مدیریت پروفایل‌های نویسندگان.
    """

    queryset = AuthorProfile.objects.all()
    serializer_class = AuthorProfileSerializer
    permission_classes = [IsAuthorProfileOwnerOrAdmin]


class PkOrSlugLookupMixin:
    """Resolve detail objects by integer primary key or Unicode slug."""

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs[lookup_url_kwarg]

        if str(lookup_value).isdigit():
            obj = queryset.filter(pk=int(lookup_value)).first()
            if obj is not None:
                self.check_object_permissions(self.request, obj)
                return obj

        obj = queryset.filter(slug=lookup_value).first()
        if obj is None:
            raise NotFound("No matching record was found.")
        self.check_object_permissions(self.request, obj)
        return obj


def _id_or_slug_schema_decorator(resource_name):
    param = OpenApiParameter(
        name="id",
        type=str,
        location=OpenApiParameter.PATH,
        description=f"Unique integer ID or Unicode slug identifying this {resource_name}.",
    )
    return extend_schema_view(
        retrieve=extend_schema(parameters=[param]),
        update=extend_schema(parameters=[param]),
        partial_update=extend_schema(parameters=[param]),
        destroy=extend_schema(parameters=[param]),
    )


@_id_or_slug_schema_decorator("category")
class CategoryViewSet(PkOrSlugLookupMixin, viewsets.ModelViewSet):
    """
    EN: ViewSet for managing article categories.
    FA: ViewSet برای مدیریت دسته‌بندی‌های مقاله.
    """

    queryset = Category.objects.select_related("parent").all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminUserOrReadOnly]
    filter_backends = [NormalizedSearchFilter]
    search_fields = ["name", "slug"]

    def list(self, request, *args, **kwargs):
        """
        EN: Lists categories with Level 4 (Long Cache) when unsearched.
        FA: لیست دسته‌بندی‌ها را با کش طولانی‌مدت بازمی‌گرداند.
        """
        def rebuild():
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return serializer.data

        search_query = (request.query_params.get("search") or "").strip()
        if search_query:
            return _set_public_cache_headers(request, Response(rebuild()), 60, 120, 300)

        cache_key = build_cache_key("posts", "category_list", "list")
        data = cache_manager.get_or_create(
            key=cache_key,
            rebuild_callback=rebuild,
            group="categories",
            soft_ttl_sec=86400,
            hard_ttl_sec=604800,
        )
        return _set_public_cache_headers(request, Response(data), 300, 900, 1800)


@_id_or_slug_schema_decorator("tag")
class TagViewSet(PkOrSlugLookupMixin, viewsets.ModelViewSet):
    """
    EN: ViewSet for managing article tags.
    FA: ViewSet برای مدیریت برچسب‌های مقاله.
    """

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAdminUserOrReadOnly]
    filter_backends = [NormalizedSearchFilter]
    search_fields = ["name", "slug"]

    def list(self, request, *args, **kwargs):
        """
        EN: Lists tags with Level 4 (Long Cache) when unsearched.
        FA: لیست برچسب‌ها را با کش طولانی‌مدت بازمی‌گرداند.
        """
        def rebuild():
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return serializer.data

        search_query = (request.query_params.get("search") or "").strip()
        if search_query:
            return _set_public_cache_headers(request, Response(rebuild()), 60, 120, 300)

        cache_key = build_cache_key("posts", "tag_list", "list")
        data = cache_manager.get_or_create(
            key=cache_key,
            rebuild_callback=rebuild,
            group="tags",
            soft_ttl_sec=86400,
            hard_ttl_sec=604800,
        )
        return _set_public_cache_headers(request, Response(data), 300, 900, 1800)


class SeriesViewSet(viewsets.ModelViewSet):
    """
    EN: ViewSet for managing article series.
    FA: ViewSet برای مدیریت مجموعه‌های مقاله.
    """

    queryset = Series.objects.all()
    serializer_class = SeriesSerializer
    permission_classes = [IsAdminUserOrReadOnly]
    filter_backends = [NormalizedSearchFilter]
    search_fields = ["title", "slug"]


class RevisionViewSet(viewsets.ModelViewSet):
    """
    EN: ViewSet for viewing article revisions.
    FA: ViewSet برای مشاهده بازنگری‌های مقاله.
    """

    queryset = Revision.objects.all()
    serializer_class = RevisionSerializer
    permission_classes = [IsAdminUser]


class PodcastCategoryViewSet(viewsets.ModelViewSet):
    """
    EN: ViewSet for managing podcast categories.
    FA: ViewSet برای مدیریت دسته‌بندی‌های پادکست.
    """

    queryset = PodcastCategory.objects.all()
    serializer_class = PodcastCategorySerializer
    permission_classes = [IsAdminUserOrReadOnly]
    filter_backends = [DjangoFilterBackend, NormalizedSearchFilter]
    filterset_fields = ["is_active"]
    search_fields = ["title", "slug"]


class PodcastViewSet(viewsets.ModelViewSet):
    """
    EN: ViewSet for managing podcasts.
    FA: ViewSet برای مدیریت پادکست‌ها.
    """

    queryset = Podcast.objects.select_related("category").all()
    serializer_class = PodcastSerializer
    permission_classes = [IsAdminUserOrReadOnly]
    filter_backends = [DjangoFilterBackend, NormalizedSearchFilter, OrderingFilter]
    filterset_fields = ["category", "media_type", "is_active"]
    search_fields = ["title", "description"]
    ordering_fields = ["published_date", "view_count", "episode_number", "id"]
    ordering = ["-published_date", "-id"]
    lookup_field = "slug"

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.view_count += 1
        obj.save(update_fields=["view_count"])
        serializer = self.get_serializer(obj)
        return Response(serializer.data)


class GalleryItemViewSet(viewsets.ModelViewSet):
    """
    EN: ViewSet for managing gallery items.
    FA: ViewSet برای مدیریت گالری تصاویر.
    """

    queryset = GalleryItem.objects.all()
    serializer_class = GalleryItemSerializer
    permission_classes = [IsAdminUserOrReadOnly]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["is_active"]
    ordering_fields = ["order", "id"]
    ordering = ["order", "-id"]


@extend_schema(
    responses={
        200: {
            "type": "object",
            "properties": {
                "articles_count": {"type": "integer"},
                "podcasts_count": {"type": "integer"},
                "images_count": {"type": "integer"},
                "gallery_count": {"type": "integer"},
                "articles": {"type": "integer"},
                "podcasts": {"type": "integer"},
                "images": {"type": "integer"},
            },
        }
    },
    description="Returns aggregate total counts for published articles, active podcasts, and images.",
)
@api_view(["GET"])
@permission_classes([AllowAny])
def content_counts(request):
    """
    EN: Returns total counts for published articles, podcasts, and images with caching.
    FA: تعداد کل مقاله‌های منتشر شده، پادکست‌ها و تصاویر را با کشینگ بازمی‌گرداند.
    """
    cache_key = build_cache_key("posts", "content_counts", "global")

    def rebuild():
        now = timezone.now()
        articles_cnt = Article.objects.filter(
            status="published", published_at__lte=now
        ).count()
        podcasts_cnt = Podcast.objects.filter(is_active=True).count()
        images_cnt = (
            Media.objects.filter(is_deleted=False)
            .filter(Q(type="image") | Q(mime__startswith="image/"))
            .count()
        )
        gallery_cnt = GalleryItem.objects.filter(is_active=True).count()

        return {
            "articles_count": articles_cnt,
            "podcasts_count": podcasts_cnt,
            "images_count": images_cnt,
            "gallery_count": gallery_cnt,
            "articles": articles_cnt,
            "podcasts": podcasts_cnt,
            "images": images_cnt,
        }

    data = cache_manager.get_or_create(
        key=cache_key,
        rebuild_callback=rebuild,
        group="counts",
        soft_ttl_sec=300,
        hard_ttl_sec=900,
    )
    return _set_public_cache_headers(request, Response(data), 300, 600, 900)
