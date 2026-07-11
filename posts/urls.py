from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from .views import (
    AuthorProfileViewSet,
    CategoryViewSet,
    GalleryItemViewSet,
    PodcastCategoryViewSet,
    PodcastViewSet,
    PostCommentViewSet,
    PostViewSet,
    RevisionViewSet,
    SeriesViewSet,
    TagViewSet,
    publish_post,
    related_posts,
)

app_name = "posts"

router = DefaultRouter()
router.register(r"posts", PostViewSet, basename="post")

posts_router = routers.NestedSimpleRouter(router, r"posts", lookup="post")
posts_router.register(r"comments", PostCommentViewSet, basename="post-comments")

router.register(r"authors", AuthorProfileViewSet)
router.register(r"categories", CategoryViewSet)
router.register(r"tags", TagViewSet)
router.register(r"series", SeriesViewSet)
router.register(r"revisions", RevisionViewSet)
router.register(r"podcast-categories", PodcastCategoryViewSet)
router.register(r"podcasts", PodcastViewSet)
router.register(r"gallery-items", GalleryItemViewSet)

urlpatterns = [
    path("posts/<slug:slug>/publish/", publish_post, name="post-publish"),
    path("posts/<slug:slug>/related/", related_posts, name="post-related"),
    path("", include(router.urls)),
    path("", include(posts_router.urls)),
]
