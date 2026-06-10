from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from users.auth_utils import should_never_lockout_staff
from unittest.mock import MagicMock

User = get_user_model()

class AuthUtilsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_should_never_lockout_staff_true(self):
        user = User.objects.create(username="staffuser", is_staff=True, phone_number="+989120000001")
        request = self.factory.post('/', {'username': 'staffuser'})
        self.assertTrue(should_never_lockout_staff(request))

    def test_should_never_lockout_staff_false_for_regular_user(self):
        user = User.objects.create(username="regularuser", is_staff=False, phone_number="+989120000002")
        request = self.factory.post('/', {'username': 'regularuser'})
        self.assertFalse(should_never_lockout_staff(request))

    def test_should_never_lockout_staff_false_for_non_existent_user(self):
        request = self.factory.post('/', {'username': 'ghost'})
        self.assertFalse(should_never_lockout_staff(request))

    def test_should_never_lockout_staff_false_no_username(self):
        request = self.factory.post('/', {})
        self.assertFalse(should_never_lockout_staff(request))
