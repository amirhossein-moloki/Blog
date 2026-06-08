import logging
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from google.auth import exceptions as google_exceptions
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from .models import User
from .permissions import (IsAdminUser, IsOwnerOrAdmin)
from .serializers import (CustomTokenObtainPairSerializer,
                          UserCreateSerializer,
                          UserReadOnlySerializer, UserSerializer,
                          GoogleLoginSerializer)
from .services import (ApplicationError, send_otp_service,
                       verify_otp_service)

logger = logging.getLogger(__name__)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        user = serializer.user
        if not settings.DEBUG and not user.is_staff:
            return Response(
                {"error": _("You are not authorized to login from here.")},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(serializer.validated_data, status=status.HTTP_200_OK)

class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing users.
    """
    queryset = User.objects.all()
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["username", "email"]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            if self.action == "retrieve" and self.request.user.is_authenticated and self.get_object() == self.request.user:
                return UserSerializer
            return UserReadOnlySerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ["send_otp", "verify_otp", "create"]:
            return [AllowAny()]
        if self.action in ["list", "retrieve"]:
            return [IsOwnerOrAdmin()]
        if self.action in ["update", "partial_update", "destroy"]:
            return [IsOwnerOrAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and user.is_staff:
            return queryset
        if user.is_authenticated:
            return queryset.filter(pk=user.pk)
        return queryset.none()

    @action(detail=False, methods=["post"])
    def send_otp(self, request):
        identifier = request.data.get("identifier")
        try:
            send_otp_service(identifier=identifier)
            return Response(
                {"message": _("OTP sent successfully.")}, status=status.HTTP_200_OK
            )
        except ApplicationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def verify_otp(self, request):
        identifier = request.data.get("identifier")
        code = request.data.get("code")
        try:
            user = verify_otp_service(identifier=identifier, code=code)
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            )
        except ApplicationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="me",
    )
    def me(self, request):
        user = self.get_queryset().get(pk=request.user.pk)
        serializer = UserSerializer(user, context={"request": request})
        return Response(serializer.data)

@extend_schema(request=GoogleLoginSerializer, responses={200: CustomTokenObtainPairSerializer})
class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("id_token")
        if not token:
            return Response(
                {"error": _("ID token is required.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not settings.GOOGLE_CLIENT_ID:
            logger.error("Google OAuth client ID is not configured")
            return Response(
                {"error": _("Google OAuth is not configured on the server.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            id_info = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
        except ValueError as exc:
            logger.warning("Invalid Google ID token: %s", exc)
            return Response(
                {"error": f"{_('Invalid token')}: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except google_exceptions.TransportError as exc:
            logger.error("Failed to verify Google token with Google services: %s", exc)
            return Response(
                {"error": _("Unable to verify token with Google at this time.")},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception:
            logger.exception("Unexpected error during Google login")
            return Response(
                {"error": _("An unexpected error occurred. Please try again later.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        email = id_info.get("email")
        if not email:
            return Response(
                {"error": _("Email not found in token.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": _("User with this email does not exist.")},
                status=status.HTTP_404_NOT_FOUND,
            )

        refresh = RefreshToken.for_user(user)
        return Response({"refresh": str(refresh), "access": str(refresh.access_token)})
