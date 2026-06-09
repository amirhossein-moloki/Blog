from rest_framework import serializers
from django.contrib.auth import get_user_model
from jalali_date import datetime2jalali
from .models import Comment, Reaction

User = get_user_model()

class JalaliDateTimeField(serializers.ReadOnlyField):
    def to_representation(self, value):
        if value:
            return datetime2jalali(value).strftime('%Y/%m/%d %H:%M:%S')
        return None

class CommentUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'profile_picture')

class CommentSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    created_at = JalaliDateTimeField()

    class Meta:
        model = Comment
        fields = ('id', 'post', 'user', 'parent', 'content', 'created_at', 'status')

class CommentListSerializer(serializers.ModelSerializer):
    user = CommentUserSerializer(read_only=True)
    created_at = JalaliDateTimeField()
    likes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Comment
        fields = ('id', 'user', 'content', 'created_at', 'parent', 'likes_count')

class ReactionSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    created_at = JalaliDateTimeField()

    class Meta:
        model = Reaction
        fields = ('id', 'user', 'reaction', 'content_type', 'object_id', 'created_at')

    def validate(self, attrs):
        content_type = attrs['content_type']
        object_id = attrs['object_id']
        ModelClass = content_type.model_class()

        if not ModelClass.objects.filter(pk=object_id).exists():
            raise serializers.ValidationError("The target object does not exist.")

        return attrs
