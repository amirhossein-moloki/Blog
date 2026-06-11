from django.core.files.uploadedfile import UploadedFile
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    pass


class UserReadOnlySerializer(serializers.ModelSerializer):
    """Serializer for public User profiles (read-only)."""

    role = serializers.SerializerMethodField()

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_role(self, obj):
        return obj.role

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
    password = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )
    password_confirm = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "password_confirm",
        )

    def validate(self, data):
        if data.get("password") != data.get("password_confirm"):
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
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
            "profile_picture",
            "role",
        )
        read_only_fields = ("id", "role")

    def _strip_non_file_profile_picture(self, data):
        if not hasattr(data, "get"):
            return data

        profile_picture = data.get("profile_picture")

        if profile_picture is not None and not isinstance(
            profile_picture, UploadedFile
        ):
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
