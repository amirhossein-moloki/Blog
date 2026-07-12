from django.db.models import Count, Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from common.mixins import DynamicSerializerViewMixin
from common.pagination import CustomPageNumberPagination
from common.permissions import (
    IsAdminUserOrReadOnly,
    IsArticleAuthorOrAdmin,
    IsAuthorProfileOwnerOrAdmin,
)
from interactions.models import Comment
from interactions.serializers import CommentListSerializer
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
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
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

    def get_queryset(self):
        """
        EN:
        Optimizes the queryset using select_related and prefetch_related based on requested fields.
        Also handles visibility rules and localization.

        FA:
        QuerySet را با استفاده از select_related و prefetch_related بر اساس فیلدهای درخواستی بهینه می‌کند.
        همچنین قوانین مشاهده‌پذیری و بومی‌سازی را مدیریت می‌کند.
        """
        lang = self.request.query_params.get("lang", "en")
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
            if "category" in fields:
                selects.add("category")
            if "cover_image" in fields:
                selects.add("cover_image")
            if "tags" in fields:
                prefetches.add("tags")
            if "likes_count" in fields:
                prefetches.add("reactions")

            if selects:
                queryset = queryset.select_related(*selects)
            if prefetches:
                queryset = queryset.prefetch_related(*prefetches)

            user = self.request.user
            if user.is_authenticated and user.is_staff:
                return queryset
            if user.is_authenticated:
                return queryset.filter(
                    Q(status="published", published_at__lte=timezone.now())
                    | Q(author__user=user, status__in=["draft", "review"])
                ).distinct()
            return queryset.filter(status="published", published_at__lte=timezone.now())
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

            if selects:
                queryset = queryset.select_related(*selects)
            if prefetches:
                queryset = queryset.prefetch_related(*prefetches)
            return queryset

    def perform_create(self, serializer):
        """
        EN: Associates the article with the author profile of the current user.
        FA: مقاله را به پروفایل نویسندگی کاربر فعلی مرتبط می‌کند.
        """
        try:
            author_profile = AuthorProfile.objects.get(user=self.request.user)
        except AuthorProfile.DoesNotExist:
            raise PermissionDenied("You do not have permission to create an article.")
        serializer.save(author=author_profile)

    def retrieve(self, request, *args, **kwargs):
        """
        EN: Increments the view count and returns article details.
        FA: تعداد بازدیدها را افزایش داده و جزئیات مقاله را بازمی‌گرداند.
        """
        obj = self.get_object()
        obj.views_count += 1
        obj.save(update_fields=["views_count"])
        serializer = self.get_serializer(obj)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def similar(self, request, slug=None):
        """
        EN: Returns similar articles based on the category.
        FA: مقاله‌های مشابه را بر اساس دسته‌بندی بازمی‌گرداند.
        """
        try:
            current_article = self.get_object()
        except Article.DoesNotExist:
            raise NotFound(
                "The requested article to find similar articles was not found."
            )

        if not current_article.category:
            return Response([])

        similar_articles = (
            Article.objects.filter(
                status="published", category=current_article.category
            )
            .exclude(pk=current_article.pk)
            .order_by("-published_at", "-id")[:5]
        )

        serializer = ArticleListSerializer(similar_articles, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="same-category")
    def same_category(self, request, slug=None):
        """
        EN: Returns paginated articles from the same category.
        FA: مقاله‌های هم‌دسته‌بندی را به صورت صفحه‌بندی شده بازمی‌گرداند.
        """
        current_article = self.get_object()

        if not current_article.category:
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

        category_articles = (
            Article.objects.filter(
                status="published",
                category=current_article.category,
                published_at__lte=timezone.now(),
            )
            .exclude(pk=current_article.pk)
            .order_by("-published_at", "-id")
        )

        paginated_articles = paginator.paginate_queryset(
            category_articles, request, view=self
        )
        serializer = ArticleListSerializer(
            paginated_articles, many=True, context=self.get_serializer_context()
        )
        return paginator.get_paginated_response(serializer.data)

    @action(detail=False, methods=["get"], url_path="slug/(?P<slug>[^/.]+)")
    def by_slug(self, request, slug=None):
        """
        EN: Endpoint to retrieve a single article by its slug and language.
        FA: اندپوینت برای دریافت یک مقاله واحد با استفاده از اسلاگ و زبان آن.
        """
        lang = request.query_params.get("lang", "en")
        try:
            # EN: Filter by translation slug
            # FA: فیلتر بر اساس اسلاگ ترجمه
            article = (
                self.get_queryset()
                .filter(translations__slug=slug, translations__language_code=lang)
                .first()
            )
            if not article:
                # EN: Fallback: Try default language if translation not found for requested lang
                # FA: جایگزین: تلاش برای زبان پیش‌فرض اگر ترجمه برای زبان درخواستی یافت نشد
                article = self.get_queryset().filter(translations__slug=slug).first()

            if not article:
                raise Article.DoesNotExist
        except Article.DoesNotExist:
            raise NotFound("No article was found with this slug.")

        serializer = ArticleDetailSerializer(
            article, context=self.get_serializer_context()
        )
        return Response(serializer.data)


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
    try:
        article = Article.objects.get(translations__slug=slug)
    except Article.DoesNotExist:
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
    try:
        current_article = Article.objects.get(translations__slug=slug)
    except Article.DoesNotExist:
        raise NotFound("The requested article to find related articles was not found.")

    paginator = CustomPageNumberPagination()
    tag_ids = current_article.tags.values_list("id", flat=True)

    if not tag_ids:
        related = Article.objects.none()
    else:
        related = (
            Article.objects.filter(status="published", tags__in=tag_ids)
            .exclude(pk=current_article.pk)
            .distinct()
        )
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


class CategoryViewSet(viewsets.ModelViewSet):
    """
    EN: ViewSet for managing article categories.
    FA: ViewSet برای مدیریت دسته‌بندی‌های مقاله.
    """

    queryset = Category.objects.select_related("parent").all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminUserOrReadOnly]


class TagViewSet(viewsets.ModelViewSet):
    """
    EN: ViewSet for managing article tags.
    FA: ViewSet برای مدیریت برچسب‌های مقاله.
    """

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAdminUserOrReadOnly]


class SeriesViewSet(viewsets.ModelViewSet):
    """
    EN: ViewSet for managing article series.
    FA: ViewSet برای مدیریت مجموعه‌های مقاله.
    """

    queryset = Series.objects.all()
    serializer_class = SeriesSerializer
    permission_classes = [IsAdminUserOrReadOnly]


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
    filter_backends = [DjangoFilterBackend, SearchFilter]
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
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
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
