from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework import authentication
from rest_framework import exceptions

User = get_user_model()

class StaticAPIKeyAuthentication(authentication.BaseAuthentication):
    """
    EN:
    Custom authentication class that uses a static API Key.
    The key is expected in the 'X-API-Key' header.
    If valid, it authenticates the first superuser found in the system.

    FA:
    کلاس احراز هویت سفارشی که از یک کلید API ثابت استفاده می‌کند.
    کلید در هدر 'X-API-Key' انتظار می‌رود.
    در صورت معتبر بودن، اولین ابرکاربر (superuser) موجود در سیستم را احراز هویت می‌کند.
    """

    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY')
        if not api_key:
            return None

        static_key = getattr(settings, 'STATIC_API_KEY', None)
        if not static_key:
            return None

        if api_key != static_key:
            raise exceptions.AuthenticationFailed('Invalid API Key')

        # EN: Authenticate as the first superuser
        # FA: احراز هویت به عنوان اولین ابرکاربر
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            raise exceptions.AuthenticationFailed('No superuser found in the system')

        return (user, None)
