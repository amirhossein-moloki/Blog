from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly

from common.pagination import CustomPageNumberPagination
from users.permissions import IsOwnerOrAdmin

from .models import Comment, Reaction
from .serializers import CommentSerializer, ReactionSerializer
from .tasks import notify_author_on_new_comment


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrAdmin]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        if user.is_authenticated and user.is_staff:
            return queryset

        return queryset.filter(status="approved")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        notify_author_on_new_comment.delay(serializer.instance.id)


class ReactionViewSet(viewsets.ModelViewSet):
    queryset = Reaction.objects.all()
    serializer_class = ReactionSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        queryset = super().get_queryset()

        user = self.request.user
        if user.is_authenticated and user.is_staff:
            return queryset

        return queryset.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
