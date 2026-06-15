import logging

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User
from .permissions import IsAdminUser, IsOwnerOrAdmin
from .serializers import (
    CustomTokenObtainPairSerializer,
    UserCreateSerializer,
    UserReadOnlySerializer,
    UserSerializer,
)

logger = logging.getLogger(__name__)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    EN: Custom JWT token obtain view using the custom serializer.
    FA: View سفارشی دریافت توکن JWT با استفاده از سریالایزر سفارشی.
    """

    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        """
        EN: Handles JWT token generation for a user.
        FA: تولید توکن JWT برای یک کاربر را مدیریت می‌کند.
        """
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    """
    EN:
    ViewSet for managing users, providing CRUD operations with tailored serializers.
    Restricts access based on administrative roles or account ownership.

    FA:
    ViewSet برای مدیریت کاربران، ارائه عملیات CRUD با سریالایزرهای اختصاصی.
    دسترسی را بر اساس نقش‌های مدیریتی یا مالکیت حساب محدود می‌کند.
    """

    queryset = User.objects.all()
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["username", "email"]

    def get_serializer_class(self):
        """
        EN: Determines which serializer to use based on the action and user context.
        FA: بر اساس اکشن و شرایط کاربر، سریالایزر مناسب را تعیین می‌کند.
        """
        if self.action in ("list", "retrieve"):
            if (
                self.action == "retrieve"
                and self.request.user.is_authenticated
                and self.get_object() == self.request.user
            ):
                return UserSerializer
            return UserReadOnlySerializer
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        """
        EN: Returns the appropriate permissions for each action.
        FA: مجوزهای مناسب برای هر اکشن را بازمی‌گرداند.
        """
        if self.action == "create":
            return [AllowAny()]
        if self.action in ["list", "retrieve"]:
            return [IsOwnerOrAdmin()]
        if self.action in ["update", "partial_update", "destroy"]:
            return [IsOwnerOrAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        """
        EN: Returns a filtered queryset where regular users can only see their own profile.
        FA: یک QuerySet فیلتر شده بازمی‌گرداند که کاربران عادی فقط پروفایل خودشان را ببینند.
        """
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and user.is_staff:
            return queryset
        if user.is_authenticated:
            return queryset.filter(pk=user.pk)
        return queryset.none()

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="me",
    )
    def me(self, request):
        """
        EN: Endpoint to retrieve the currently authenticated user's profile.
        FA: اندپوینت برای دریافت پروفایل کاربر فعلی که احراز هویت شده است.
        """
        user = self.get_queryset().get(pk=request.user.pk)
        serializer = UserSerializer(user, context={"request": request})
        return Response(serializer.data)
