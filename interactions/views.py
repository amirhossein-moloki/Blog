from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly

from common.pagination import CustomPageNumberPagination
from users.permissions import IsOwnerOrAdmin

from .models import Comment, Reaction
from .serializers import CommentSerializer, ReactionSerializer
from .tasks import notify_author_on_new_comment


class CommentViewSet(viewsets.ModelViewSet):
    """
    EN:
    ViewSet for managing comments.
    Regular users only see approved comments, while staff can see all.
    Triggers a notification task upon comment creation.

    FA:
    ViewSet برای مدیریت نظرات.
    کاربران عادی فقط نظرات تایید شده را می‌بینند، در حالی که کارکنان به همه نظرات دسترسی دارند.
    هنگام ایجاد نظر، یک تسک اعلان را اجرا می‌کند.
    """

    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrAdmin]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        """
        EN: Returns a queryset of comments, filtered by status for regular users.
        FA: یک QuerySet از نظرات را بازمی‌گرداند که برای کاربران عادی بر اساس وضعیت فیلتر شده است.
        """
        user = self.request.user
        queryset = super().get_queryset()

        if user.is_authenticated and user.is_staff:
            return queryset

        return queryset.filter(status="approved")

    def perform_create(self, serializer):
        """
        EN: Saves the comment with the current user and triggers an author notification.
        FA: نظر را با کاربر فعلی ذخیره کرده و یک اعلان برای نویسنده ارسال می‌کند.
        """
        serializer.save(user=self.request.user)
        notify_author_on_new_comment.delay(serializer.instance.id)


class ReactionViewSet(viewsets.ModelViewSet):
    """
    EN:
    ViewSet for managing reactions (likes, emojis).
    Users can only manage their own reactions.

    FA:
    ViewSet برای مدیریت واکنش‌ها (لایک‌ها، اموجی‌ها).
    کاربران فقط می‌توانند واکنش‌های خودشان را مدیریت کنند.
    """

    queryset = Reaction.objects.all()
    serializer_class = ReactionSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        """
        EN: Returns the user's own reactions, or all reactions for staff.
        FA: واکنش‌های خود کاربر، یا تمامی واکنش‌ها را برای کارکنان بازمی‌گرداند.
        """
        queryset = super().get_queryset()

        user = self.request.user
        if user.is_authenticated and user.is_staff:
            return queryset

        return queryset.filter(user=user)

    def perform_create(self, serializer):
        """
        EN: Associates the reaction with the currently authenticated user.
        FA: واکنش را به کاربر احراز هویت شده فعلی مرتبط می‌کند.
        """
        serializer.save(user=self.request.user)
