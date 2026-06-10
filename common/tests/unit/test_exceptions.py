from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from common.exceptions import custom_exception_handler
from rest_framework.exceptions import NotAuthenticated, PermissionDenied, APIException
from rest_framework.views import APIView
from django.http import Http404

User = get_user_model()

class ExceptionHandlerTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = APIView()

    def test_not_authenticated_handler(self):
        exc = NotAuthenticated()
        request = self.factory.get('/')
        context = {'view': self.view, 'request': request}
        response = custom_exception_handler(exc, context)

        self.assertEqual(response.status_code, 401)
        self.assertIn("احراز هویت", response.data['messagesList'][0])

    def test_permission_denied_handler(self):
        exc = PermissionDenied()
        request = self.factory.get('/')
        context = {'view': self.view, 'request': request}
        response = custom_exception_handler(exc, context)

        self.assertEqual(response.status_code, 403)
        self.assertIn("دسترسی", response.data['messagesList'][0])

    def test_not_found_handler(self):
        exc = Http404()
        request = self.factory.get('/')
        context = {'view': self.view, 'request': request}
        response = custom_exception_handler(exc, context)

        self.assertEqual(response.status_code, 404)
        self.assertIn("یافت نشد", response.data['messagesList'][0])

    def test_generic_api_exception(self):
        exc = APIException("Some error")
        request = self.factory.get('/')
        context = {'view': self.view, 'request': request}
        response = custom_exception_handler(exc, context)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data['messagesList'], ["Some error"])

    def test_non_api_exception(self):
        exc = ValueError("Fatal error")
        request = self.factory.get('/')
        context = {'view': self.view, 'request': request}
        # This will trigger logger and return 500
        with self.settings(DEBUG=False):
            response = custom_exception_handler(exc, context)
            self.assertEqual(response.status_code, 500)
            self.assertIn("یک خطای پیش‌بینی نشده", response.data['messagesList'][0])

        with self.settings(DEBUG=True):
            response = custom_exception_handler(exc, context)
            self.assertEqual(response.status_code, 500)
            self.assertIn("Fatal error", response.data['messagesList'][0])
