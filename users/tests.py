from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from blog.tests.base import BaseAPITestCase
from .models import User, OTP
from .services import verify_otp_service

class UserViewSetAPITest(BaseAPITestCase):

    def test_user_can_update_own_profile(self):
        self._authenticate()
        url = reverse('user-detail', kwargs={'pk': self.user.pk})
        data = {'username': 'new_username'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'new_username')

    def test_user_cannot_update_other_profile(self):
        self._authenticate()
        other_user = self.staff_user
        url = reverse('user-detail', kwargs={'pk': other_user.pk})
        data = {'username': 'should_not_work'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_update_other_profile(self):
        self._authenticate_as_staff()
        other_user = self.user
        url = reverse('user-detail', kwargs={'pk': other_user.pk})
        data = {'username': 'admin_was_here'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        other_user.refresh_from_db()
        self.assertEqual(other_user.username, 'admin_was_here')

    def test_admin_can_delete_user(self):
        self._authenticate_as_staff()
        user_to_delete = self.user
        url = reverse('user-detail', kwargs={'pk': user_to_delete.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(pk=user_to_delete.pk).exists())

class OTPServiceTest(BaseAPITestCase):
    def test_verify_otp_handles_existing_duplicate_case_insensitive_emails(self):
        email1 = "DuplicateCase@Example.com"
        email2 = "duplicatecase@example.com"
        user1 = User.objects.create(username=email1, email=email1, phone_number="+989999999991")
        user2 = User.objects.create(username=email2, email=email2, phone_number="+989999999992")
        initial_user_count = User.objects.count()
        otp_code = "123456"
        OTP.objects.create(identifier=email1, code=otp_code)
        verified_user = verify_otp_service(identifier=email1, code=otp_code)
        self.assertIsNotNone(verified_user)
        self.assertIn(verified_user.pk, [user1.pk, user2.pk])
        self.assertEqual(User.objects.count(), initial_user_count)

class UserSignalTests(TestCase):
    def test_new_user_creation_signal(self):
        user = User.objects.create_user(username='newusertest', phone_number='+989123456789', password='testpassword')
        user.refresh_from_db()
        # After refactoring, wallet and referral_code are removed.
        # Just check that the user was created successfully.
        self.assertEqual(user.username, 'newusertest')
