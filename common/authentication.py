from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import authentication, exceptions

User = get_user_model()


class StaticAPIKeyAuthentication(authentication.BaseAuthentication):
    """
    EN:
    Custom authentication class that uses a static API Key.
    The key is expected in the 'X-API-Key' header.
    If valid, it authenticates the user specified in 'X-Test-User' header,
    or the first superuser found in the system if no user is specified.

    FA:
    کلاس احراز هویت سفارشی که از یک کلید API ثابت استفاده می‌کند.
    کلید در هدر 'X-API-Key' انتظار می‌رود.
    در صورت معتبر بودن، کاربر مشخص شده در هدر 'X-Test-User' را احراز هویت می‌کند،
    یا اگر کاربری مشخص نشده باشد، اولین ابرکاربر (superuser) موجود در سیستم را احراز هویت می‌کند.
    """

    def authenticate(self, request):
        api_key = request.META.get("HTTP_X_API_KEY")
        if not api_key:
            return None

        static_key = getattr(settings, "STATIC_API_KEY", None)
        if not static_key:
            return None

        if api_key != static_key:
            raise exceptions.AuthenticationFailed("Invalid API Key")

        # EN: Optional header to specify which user to authenticate as for testing
        # FA: هدر اختیاری برای مشخص کردن اینکه برای تست به عنوان چه کاربری احراز هویت شود
        test_username = request.META.get("HTTP_X_TEST_USER")
        if test_username:
            user = User.objects.filter(username=test_username).first()
            if not user:
                raise exceptions.AuthenticationFailed(
                    f"Test user {test_username} not found"
                )
            return (user, None)

        # EN: Fallback to the first superuser
        # FA: جایگزین به اولین ابرکاربر
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            return None

        return (user, None)
