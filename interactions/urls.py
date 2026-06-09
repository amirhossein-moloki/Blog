from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CommentViewSet, ReactionViewSet

app_name = 'interactions'

router = DefaultRouter()
router.register(r'comments', CommentViewSet, basename='comment')
router.register(r'reactions', ReactionViewSet, basename='reaction')

urlpatterns = [
    path('', include(router.urls)),
]
