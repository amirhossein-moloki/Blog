from django.core.files.uploadedfile import UploadedFile
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    EN: Custom JWT token serializer extending SimpleJWT's default.
    FA: سریالایزر توکن JWT سفارشی که سریالایزر پیش‌فرض SimpleJWT را گسترش می‌دهد.
    """

    pass


class UserReadOnlySerializer(serializers.ModelSerializer):
    """
    EN: Serializer for public User profiles (read-only access).
    FA: سریالایزر برای پروفایل‌های عمومی کاربران (دسترسی فقط خواندنی).
    """

    role = serializers.SerializerMethodField()

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_role(self, obj):
        """
        EN: Returns the roles/groups associated with the user.
        FA: نقش‌ها/گروه‌های مرتبط با کاربر را بازمی‌گرداند.
        """
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
    """
    EN: Serializer for registering a new User.
    FA: سریالایزر برای ثبت‌نام یک کاربر جدید.
    """

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
        """
        EN: Ensures the password and password confirmation match.
        FA: اطمینان حاصل می‌کند که رمز عبور و تاییدیه رمز عبور یکسان باشند.
        """
        if data.get("password") != data.get("password_confirm"):
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        """
        EN: Creates and returns a new user instance with the hashed password.
        FA: یک نمونه کاربر جدید با رمز عبور هش شده ایجاد کرده و بازمی‌گرداند.
        """
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    """
    EN: Serializer for the User model providing full access for the account owner.
    FA: سریالایزر برای مدل کاربر که دسترسی کامل را برای صاحب حساب فراهم می‌کند.
    """

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
        """
        EN:
        Prevents updating profile_picture if the provided value is not a file.
        This handles cases where the existing URL is sent back in a multi-part form.

        FA:
        در صورتی که مقدار ارائه شده فایل نباشد، از به‌روزرسانی profile_picture جلوگیری می‌کند.
        این کار مواردی را که آدرس URL موجود در فرم چندبخشی (multi-part) بازگردانده می‌شود، مدیریت می‌کند.
        """
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
        """
        EN: Pre-processes the data before validation to handle profile picture logic.
        FA: پیش‌پردازش داده‌ها قبل از اعتبارسنجی برای مدیریت منطق تصویر پروفایل.
        """
        data = self._strip_non_file_profile_picture(data)
        return super().to_internal_value(data)

    def update(self, instance, validated_data):
        """
        EN: Custom update logic to handle profile picture field properly.
        FA: منطق به‌روزرسانی سفارشی برای مدیریت صحیح فیلد تصویر پروفایل.
        """
        if "profile_picture" not in self.initial_data:
            validated_data.pop("profile_picture", None)
        return super().update(instance, validated_data)
