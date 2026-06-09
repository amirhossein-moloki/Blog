from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend

from common.mixins import DynamicSerializerViewMixin
from common.pagination import CustomPageNumberPagination
from users.permissions import IsOwnerOrAdmin
from common.permissions import IsAdminUserOrReadOnly, IsAuthorOrAdminOrReadOnly
from .models import Post, AuthorProfile, Category, Tag, Series, Revision
from .serializers import (
    PostListSerializer, PostDetailSerializer, PostCreateUpdateSerializer,
    AuthorProfileSerializer, CategorySerializer, TagSerializer, SeriesSerializer,
    RevisionSerializer
)
from .filters import PostFilter
from interactions.serializers import CommentListSerializer
from interactions.models import Comment

class PostViewSet(DynamicSerializerViewMixin, viewsets.ModelViewSet):
    queryset = Post.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrAdminOrReadOnly]
    pagination_class = CustomPageNumberPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = PostFilter
    search_fields = ['title', 'content', 'excerpt']
    ordering_fields = ['published_at', 'views_count', 'id']
    ordering = ['-published_at', '-id']
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PostCreateUpdateSerializer
        elif self.action == 'retrieve':
            return PostDetailSerializer
        return PostListSerializer

    def get_queryset(self):
        if self.action == 'list':
            queryset = Post.objects.all()
            fields_query = self.request.query_params.get('fields')
            fields = {f.strip() for f in fields_query.split(',')} if fields_query else set()

            selects = set()
            prefetches = set()

            if not fields:
                fields = {'slug', 'title', 'excerpt', 'author', 'category', 'cover_media', 'tags', 'likes_count', 'comments_count'}

            if 'author' in fields:
                selects.add('author__avatar')
            if 'category' in fields:
                selects.add('category')
            if 'cover_media' in fields:
                selects.add('cover_media')
            if 'tags' in fields:
                prefetches.add('tags')
            if 'likes_count' in fields:
                prefetches.add('reactions')

            if selects:
                queryset = queryset.select_related(*selects)
            if prefetches:
                queryset = queryset.prefetch_related(*prefetches)

            user = self.request.user
            if user.is_authenticated and user.is_staff:
                return queryset
            if user.is_authenticated:
                return queryset.filter(
                    Q(status='published', published_at__lte=timezone.now()) |
                    Q(author__user=user, status__in=['draft', 'review'])
                ).distinct()
            return queryset.filter(status='published', published_at__lte=timezone.now())
        else:
            queryset = Post.objects.all()
            fields_query = self.request.query_params.get('fields')
            fields = {f.strip() for f in fields_query.split(',')} if fields_query else {'all'}

            selects = set()
            prefetches = set()
            all_fields = 'all' in fields

            if all_fields or 'author' in fields:
                selects.add('author__avatar')
            if all_fields or 'category' in fields:
                selects.add('category')
            if all_fields or 'cover_media' in fields:
                selects.add('cover_media')
            if all_fields or 'series' in fields:
                selects.add('series')
            if all_fields or 'og_image' in fields:
                selects.add('og_image')
            if all_fields or 'tags' in fields:
                prefetches.add('tags')
            if all_fields or 'likes_count' in fields:
                prefetches.add('reactions')
            if all_fields or 'comments' in fields:
                prefetches.add('comments__user')
            if all_fields or 'media_attachments' in fields:
                prefetches.add('media_attachments__media')

            if selects:
                queryset = queryset.select_related(*selects)
            if prefetches:
                queryset = queryset.prefetch_related(*prefetches)
            return queryset

    def perform_create(self, serializer):
        try:
            author_profile = AuthorProfile.objects.get(user=self.request.user)
        except AuthorProfile.DoesNotExist:
            raise PermissionDenied("You do not have permission to create a post.")
        serializer.save(author=author_profile)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.views_count += 1
        obj.save(update_fields=['views_count'])
        serializer = self.get_serializer(obj)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def similar(self, request, slug=None):
        try:
            current_post = self.get_object()
        except Post.DoesNotExist:
            raise NotFound('پست مورد نظر برای یافتن پست‌های مشابه پیدا نشد.')

        if not current_post.category:
            return Response([])

        similar_posts = Post.objects.filter(
            status='published',
            category=current_post.category
        ).exclude(pk=current_post.pk).order_by('-published_at', '-id')[:5]

        serializer = PostListSerializer(similar_posts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='same-category')
    def same_category(self, request, slug=None):
        current_post = self.get_object()
        paginator = self.pagination_class()

        if not current_post.category:
            return paginator.get_paginated_response([])

        category_posts = Post.objects.filter(
            status='published',
            category=current_post.category,
            published_at__lte=timezone.now()
        ).exclude(pk=current_post.pk).order_by('-published_at', '-id')

        paginated_posts = paginator.paginate_queryset(category_posts, request, view=self)
        serializer = PostListSerializer(paginated_posts, many=True, context=self.get_serializer_context())
        return paginator.get_paginated_response(serializer.data)

    @action(detail=False, methods=['get'], url_path='slug/(?P<slug>[^/.]+)')
    def by_slug(self, request, slug=None):
        try:
            post = self.get_queryset().get(slug=slug)
        except Post.DoesNotExist:
            raise NotFound('پستی با این اسلاگ یافت نشد.')

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
    serializer_class = CommentListSerializer
    pagination_class = CustomPageNumberPagination
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [OrderingFilter]
    ordering_fields = ['created_at', 'likes_count']
    ordering = ['-created_at']

    def get_queryset(self):
        post_slug = self.kwargs.get('post_slug')
        return Comment.objects.filter(
            post__slug=post_slug,
            status='approved'
        ).annotate(
            likes_count=Count('reactions', filter=Q(reactions__reaction='like'))
        ).select_related('user__authorprofile')

@extend_schema(
    responses={200: PostDetailSerializer},
    description="Publish a draft or scheduled post."
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsOwnerOrAdmin])
def publish_post(request, slug):
    try:
        post = Post.objects.get(slug=slug)
    except Post.DoesNotExist:
        raise NotFound('پستی با این مشخصات یافت نشد.')

    if post.author.user != request.user and not request.user.is_staff:
        raise PermissionDenied('شما اجازه‌ی انتشار این پست را ندارید.')

    if post.status not in ['draft', 'scheduled']:
        return Response(
            {'detail': 'تنها پست‌های پیش‌نویس یا زمان‌بندی شده را می‌توان منتشر کرد.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    post.status = 'published'
    post.published_at = timezone.now()
    post.scheduled_at = None
    post.save()
    serializer = PostDetailSerializer(post)
    return Response(serializer.data)

@extend_schema(
    responses={200: PostListSerializer(many=True)},
    description="Get related posts based on tags."
)
@api_view(['GET'])
def related_posts(request, slug):
    try:
        current_post = Post.objects.get(slug=slug)
    except Post.DoesNotExist:
        raise NotFound('پست مورد نظر برای یافتن پست‌های مرتبط پیدا نشد.')

    paginator = CustomPageNumberPagination()
    tag_ids = current_post.tags.values_list('id', flat=True)

    if not tag_ids:
        related = Post.objects.none()
    else:
        related = Post.objects.filter(
            status='published',
            tags__in=tag_ids
        ).exclude(pk=current_post.pk).distinct()
        related = related.annotate(
            common_tags=Count('tags', filter=Q(tags__in=tag_ids))
        ).order_by('-common_tags', '-published_at', '-id')

    paginated_related_posts = paginator.paginate_queryset(related, request)
    serializer = PostListSerializer(paginated_related_posts, many=True, context={'request': request})
    return paginator.get_paginated_response(serializer.data)

class AuthorProfileViewSet(viewsets.ModelViewSet):
    queryset = AuthorProfile.objects.all()
    serializer_class = AuthorProfileSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrAdmin]

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.select_related('parent').all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminUserOrReadOnly]

class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAdminUserOrReadOnly]

class SeriesViewSet(viewsets.ModelViewSet):
    queryset = Series.objects.all()
    serializer_class = SeriesSerializer
    permission_classes = [IsAdminUserOrReadOnly]

class RevisionViewSet(viewsets.ModelViewSet):
    queryset = Revision.objects.all()
    serializer_class = RevisionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrAdmin]
