from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from .views import (
    ArticleCommentViewSet,
    ArticleViewSet,
    AuthorProfileViewSet,
    CategoryViewSet,
    GalleryItemViewSet,
    PodcastCategoryViewSet,
    PodcastViewSet,
    RevisionViewSet,
    SeriesViewSet,
    TagViewSet,
    publish_article,
    related_articles,
)

app_name = "posts"

router = DefaultRouter()
router.register(r"articles", ArticleViewSet, basename="article")

articles_router = routers.NestedSimpleRouter(router, r"articles", lookup="article")
articles_router.register(
    r"comments", ArticleCommentViewSet, basename="article-comments"
)

router.register(r"authors", AuthorProfileViewSet)
router.register(r"categories", CategoryViewSet)
router.register(r"tags", TagViewSet)
router.register(r"series", SeriesViewSet)
router.register(r"revisions", RevisionViewSet)
router.register(r"podcast-categories", PodcastCategoryViewSet)
router.register(r"podcasts", PodcastViewSet)
router.register(r"gallery", GalleryItemViewSet, basename="galleryitem")

urlpatterns = [
    path("articles/<slug:slug>/publish/", publish_article, name="article-publish"),
    path("articles/<slug:slug>/related/", related_articles, name="article-related"),
    path("", include(router.urls)),
    path("", include(articles_router.urls)),
]
