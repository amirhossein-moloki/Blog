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
from common.permissions import IsAdminUserOrReadOnly, IsAuthorOrAdminOrReadOnly
from interactions.models import Comment
from interactions.serializers import CommentListSerializer
from users.permissions import IsOwnerOrAdmin

from .filters import PostFilter
from .models import AuthorProfile, Category, Post, Revision, Series, Tag
from .serializers import (
    AuthorProfileSerializer,
    CategorySerializer,
    PostCreateUpdateSerializer,
    PostDetailSerializer,
    PostListSerializer,
    RevisionSerializer,
    SeriesSerializer,
    TagSerializer,
)


class PostViewSet(DynamicSerializerViewMixin, viewsets.ModelViewSet):
    """
    EN:
    ViewSet for managing blog posts.
    Provides advanced filtering, searching, and dynamic field selection.
    Handles complex queryset optimizations and access control for drafts/scheduled posts.

    FA:
    ViewSet برای مدیریت پست‌های بلاگ.
    فیلترینگ پیشرفته، جستجو و انتخاب داینامیک فیلدها را فراهم می‌کند.
    بهینه‌سازی‌های پیچیده QuerySet و کنترل دسترسی برای پیش‌نویس‌ها و پست‌های زمان‌بندی شده را مدیریت می‌کند.
    """

    queryset = Post.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrAdminOrReadOnly]
    pagination_class = CustomPageNumberPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = PostFilter
    search_fields = ["title", "content", "excerpt"]
    ordering_fields = ["published_at", "views_count", "id"]
    ordering = ["-published_at", "-id"]
    lookup_field = "slug"

    def get_serializer_class(self):
        """
        EN: Returns the serializer class based on the action.
        FA: کلاس سریالایزر را بر اساس اکشن بازمی‌گرداند.
        """
        if self.action in ["create", "update", "partial_update"]:
            return PostCreateUpdateSerializer
        elif self.action == "retrieve":
            return PostDetailSerializer
        return PostListSerializer

    def get_queryset(self):
        """
        EN:
        Optimizes the queryset using select_related and prefetch_related based on requested fields.
        Also handles visibility rules: regular users only see published posts, authors see their drafts.

        FA:
        QuerySet را با استفاده از select_related و prefetch_related بر اساس فیلدهای درخواستی بهینه می‌کند.
        همچنین قوانین مشاهده‌پذیری را مدیریت می‌کند: کاربران عادی فقط پست‌های منتشر شده را می‌بینند، نویسندگان پیش‌نویس‌های خود را می‌بینند.
        """
        if self.action == "list":
            queryset = Post.objects.all()
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
                    "cover_media",
                    "tags",
                    "likes_count",
                    "comments_count",
                }

            if "author" in fields:
                selects.add("author__avatar")
            if "category" in fields:
                selects.add("category")
            if "cover_media" in fields:
                selects.add("cover_media")
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
            queryset = Post.objects.all()
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
            if all_fields or "category" in fields:
                selects.add("category")
            if all_fields or "cover_media" in fields:
                selects.add("cover_media")
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
        EN: Associates the post with the author profile of the current user.
        FA: پست را به پروفایل نویسندگی کاربر فعلی مرتبط می‌کند.
        """
        try:
            author_profile = AuthorProfile.objects.get(user=self.request.user)
        except AuthorProfile.DoesNotExist:
            raise PermissionDenied("You do not have permission to create a post.")
        serializer.save(author=author_profile)

    def retrieve(self, request, *args, **kwargs):
        """
        EN: Increments the view count and returns post details.
        FA: تعداد بازدیدها را افزایش داده و جزئیات پست را بازمی‌گرداند.
        """
        obj = self.get_object()
        obj.views_count += 1
        obj.save(update_fields=["views_count"])
        serializer = self.get_serializer(obj)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def similar(self, request, slug=None):
        """
        EN: Returns similar posts based on the category.
        FA: پست‌های مشابه را بر اساس دسته‌بندی بازمی‌گرداند.
        """
        try:
            current_post = self.get_object()
        except Post.DoesNotExist:
            raise NotFound("The requested post to find similar posts was not found.")

        if not current_post.category:
            return Response([])

        similar_posts = (
            Post.objects.filter(status="published", category=current_post.category)
            .exclude(pk=current_post.pk)
            .order_by("-published_at", "-id")[:5]
        )

        serializer = PostListSerializer(similar_posts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="same-category")
    def same_category(self, request, slug=None):
        """
        EN: Returns paginated posts from the same category.
        FA: پست‌های هم‌دسته‌بندی را به صورت صفحه‌بندی شده بازمی‌گرداند.
        """
        current_post = self.get_object()

        if not current_post.category:
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

        category_posts = (
            Post.objects.filter(
                status="published",
                category=current_post.category,
                published_at__lte=timezone.now(),
            )
            .exclude(pk=current_post.pk)
            .order_by("-published_at", "-id")
        )

        paginated_posts = paginator.paginate_queryset(
            category_posts, request, view=self
        )
        serializer = PostListSerializer(
            paginated_posts, many=True, context=self.get_serializer_context()
        )
        return paginator.get_paginated_response(serializer.data)

    @action(detail=False, methods=["get"], url_path="slug/(?P<slug>[^/.]+)")
    def by_slug(self, request, slug=None):
        """
        EN: Endpoint to retrieve a single post by its slug.
        FA: اندپوینت برای دریافت یک پست واحد با استفاده از اسلاگ آن.
        """
        try:
            post = self.get_queryset().get(slug=slug)
        except Post.DoesNotExist:
            raise NotFound("No post was found with this slug.")

        serializer = PostDetailSerializer(post, context=self.get_serializer_context())
        return Response(serializer.data)


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="post_slug",
            type=str,
            location=OpenApiParameter.PATH,
            description="The slug of the post to get comments for.",
        )
    ]
)
class PostCommentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    EN: ViewSet to list approved comments for a specific post.
    FA: ViewSet برای لیست کردن نظرات تایید شده برای یک پست خاص.
    """

    serializer_class = CommentListSerializer
    pagination_class = CustomPageNumberPagination
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [OrderingFilter]
    ordering_fields = ["created_at", "likes_count"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """
        EN: Returns approved comments for the specified post, annotated with likes.
        FA: نظرات تایید شده برای پست مشخص شده را به همراه تعداد لایک‌ها بازمی‌گرداند.
        """
        post_slug = self.kwargs.get("post_slug")
        return (
            Comment.objects.filter(post__slug=post_slug, status="approved")
            .annotate(
                likes_count=Count("reactions", filter=Q(reactions__reaction="like"))
            )
            .select_related("user__authorprofile")
        )


@extend_schema(
    request=None,
    responses={200: PostDetailSerializer},
    description="Publish a draft or scheduled post.",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated, IsOwnerOrAdmin])
def publish_post(request, slug):
    """
    EN: API view to manually publish a draft or scheduled post.
    FA: نمای API برای انتشار دستی یک پست پیش‌نویس یا زمان‌بندی شده.
    """
    try:
        post = Post.objects.get(slug=slug)
    except Post.DoesNotExist:
        raise NotFound("No post was found with these specifications.")

    if post.author.user != request.user and not request.user.is_staff:
        raise PermissionDenied("You do not have permission to publish this post.")

    if post.status not in ["draft", "scheduled"]:
        return Response(
            {"detail": "Only draft or scheduled posts can be published."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    post.status = "published"
    post.published_at = timezone.now()
    post.scheduled_at = None
    post.save()
    serializer = PostDetailSerializer(post)
    return Response(serializer.data)


@extend_schema(
    responses={200: PostListSerializer(many=True)},
    description="Get related posts based on tags.",
)
@api_view(["GET"])
def related_posts(request, slug):
    """
    EN: Returns related posts sharing common tags with the specified post.
    FA: پست‌های مرتبط که دارای برچسب‌های مشترک با پست مشخص شده هستند را بازمی‌گرداند.
    """
    try:
        current_post = Post.objects.get(slug=slug)
    except Post.DoesNotExist:
        raise NotFound("The requested post to find related posts was not found.")

    paginator = CustomPageNumberPagination()
    tag_ids = current_post.tags.values_list("id", flat=True)

    if not tag_ids:
        related = Post.objects.none()
    else:
        related = (
            Post.objects.filter(status="published", tags__in=tag_ids)
            .exclude(pk=current_post.pk)
            .distinct()
        )
        related = related.annotate(
            common_tags=Count("tags", filter=Q(tags__in=tag_ids))
        ).order_by("-common_tags", "-published_at", "-id")

    paginated_related_posts = paginator.paginate_queryset(related, request)
    serializer = PostListSerializer(
        paginated_related_posts, many=True, context={"request": request}
    )
    return paginator.get_paginated_response(serializer.data)


class AuthorProfileViewSet(viewsets.ModelViewSet):
    """
    EN: ViewSet for managing author profiles.
    FA: ViewSet برای مدیریت پروفایل‌های نویسندگان.
    """

    queryset = AuthorProfile.objects.all()
    serializer_class = AuthorProfileSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrAdmin]


class CategoryViewSet(viewsets.ModelViewSet):
    """
    EN: ViewSet for managing post categories.
    FA: ViewSet برای مدیریت دسته‌بندی‌های پست.
    """

    queryset = Category.objects.select_related("parent").all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminUserOrReadOnly]


class TagViewSet(viewsets.ModelViewSet):
    """
    EN: ViewSet for managing post tags.
    FA: ViewSet برای مدیریت برچسب‌های پست.
    """

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAdminUserOrReadOnly]


class SeriesViewSet(viewsets.ModelViewSet):
    """
    EN: ViewSet for managing post series.
    FA: ViewSet برای مدیریت مجموعه‌های پست.
    """

    queryset = Series.objects.all()
    serializer_class = SeriesSerializer
    permission_classes = [IsAdminUserOrReadOnly]


class RevisionViewSet(viewsets.ModelViewSet):
    """
    EN: ViewSet for viewing post revisions.
    FA: ViewSet برای مشاهده بازنگری‌های پست.
    """

    queryset = Revision.objects.all()
    serializer_class = RevisionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrAdmin]
