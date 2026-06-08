from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from .models import User
from django.core.files.uploadedfile import UploadedFile

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    pass

class UserReadOnlySerializer(serializers.ModelSerializer):
    """Serializer for public User profiles (read-only)."""

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "profile_picture",
            "role",
        )
        read_only_fields = fields

class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new User."""

    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "phone_number",
            "first_name",
            "last_name",
        )

    def create(self, validated_data):
        user = User(**validated_data)
        user.set_unusable_password()
        user.save()
        return user

class UserSerializer(serializers.ModelSerializer):
    """Serializer for the User model (full view for owner)."""

    role = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "profile_picture",
            "role",
        )
        read_only_fields = ("id", "role")

    def _strip_non_file_profile_picture(self, data):
        if not hasattr(data, "get"):
            return data

        profile_picture = data.get("profile_picture")

        if profile_picture is not None and not isinstance(profile_picture, UploadedFile):
            data = data.copy()
            data.pop("profile_picture", None)

        return data

    def to_internal_value(self, data):
        data = self._strip_non_file_profile_picture(data)
        return super().to_internal_value(data)

    def update(self, instance, validated_data):
        if "profile_picture" not in self.initial_data:
            validated_data.pop("profile_picture", None)
        return super().update(instance, validated_data)

class GoogleLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField()
