from django.contrib.auth import get_user_model
from jalali_date import datetime2jalali
from rest_framework import serializers

from .models import Comment, Reaction

User = get_user_model()


class JalaliDateTimeField(serializers.ReadOnlyField):
    """
    EN: Custom field to represent datetime in Jalali (Persian) format.
    FA: فیلد سفارشی برای نمایش تاریخ و زمان در قالب جلالی (شمسی).
    """

    def to_representation(self, value):
        """
        EN: Converts the datetime object to a Jalali date string.
        FA: تبدیل شیء datetime به رشته تاریخ جلالی.
        """
        if value:
            return datetime2jalali(value).strftime("%Y/%m/%d %H:%M:%S")
        return None


class CommentUserSerializer(serializers.ModelSerializer):
    """
    EN: Serializer for minimal User information within comments.
    FA: سریالایزر برای اطلاعات حداقلی کاربر در نظرات.
    """

    class Meta:
        model = User
        fields = ("username", "profile_picture")


class CommentSerializer(serializers.ModelSerializer):
    """
    EN: Serializer for creating and managing individual Comments.
    FA: سریالایزر برای ایجاد و مدیریت نظرات فردی.
    """

    user = serializers.PrimaryKeyRelatedField(read_only=True)
    created_at = JalaliDateTimeField()

    class Meta:
        model = Comment
        fields = ("id", "post", "user", "parent", "content", "created_at", "status")


class CommentListSerializer(serializers.ModelSerializer):
    """
    EN: Serializer for listing Comments with user details and like counts.
    FA: سریالایزر برای لیست کردن نظرات به همراه جزئیات کاربر و تعداد لایک‌ها.
    """

    user = CommentUserSerializer(read_only=True)
    created_at = JalaliDateTimeField()
    likes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Comment
        fields = ("id", "user", "content", "created_at", "parent", "likes_count")


class ReactionSerializer(serializers.ModelSerializer):
    """
    EN: Serializer for creating and managing Reactions (likes, emojis) on various objects.
    FA: سریالایزر برای ایجاد و مدیریت واکنش‌ها (لایک‌ها، اموجی‌ها) روی اشیاء مختلف.
    """

    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    created_at = JalaliDateTimeField()

    class Meta:
        model = Reaction
        fields = ("id", "user", "reaction", "content_type", "object_id", "created_at")
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=Reaction.objects.all(),
                fields=("user", "content_type", "object_id", "reaction"),
                message="You have already reacted to this object with this reaction.",
            )
        ]

    def validate(self, attrs):
        """
        EN: Validates that the target object for the reaction exists.
        FA: بررسی می‌کند که شیء هدف برای واکنش وجود داشته باشد.
        """
        content_type = attrs["content_type"]
        object_id = attrs["object_id"]
        ModelClass = content_type.model_class()

        if not ModelClass.objects.filter(pk=object_id).exists():
            raise serializers.ValidationError("The target object does not exist.")

        return attrs

    def to_representation(self, instance):
        """
        EN: Customizes the representation to include the user's primary key.
        FA: نمایش سریالایزر را برای شامل شدن کلید اصلی کاربر سفارشی می‌کند.
        """
        ret = super().to_representation(instance)
        ret["user"] = instance.user.pk
        return ret
