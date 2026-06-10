from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from users.models import User, OTP
from posts.factories import UserFactory

class AuthFlowIntegrationTest(APITestCase):
    def test_full_otp_auth_flow_new_user(self):
        # 1. Request OTP
        identifier = "+989121111111"
        send_otp_url = reverse('user-send-otp')
        response = self.client.post(send_otp_url, {'identifier': identifier})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify OTP was created in DB
        otp = OTP.objects.get(identifier=identifier)
        self.assertIsNotNone(otp.code)

        # 2. Verify OTP
        verify_otp_url = reverse('user-verify-otp')
        response = self.client.post(verify_otp_url, {
            'identifier': identifier,
            'code': otp.code
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

        access_token = response.data['access']

        # Verify user was created
        self.assertTrue(User.objects.filter(phone_number=identifier).exists())
        user = User.objects.get(phone_number=identifier)

        # 3. Access 'me' endpoint with token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        me_url = reverse('user-me')
        response = self.client.get(me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], user.username)

    def test_otp_auth_flow_existing_user(self):
        user = UserFactory(phone_number="+989122222222", username="existing_user")
        identifier = str(user.phone_number)

        # Request OTP
        self.client.post(reverse('user-send-otp'), {'identifier': identifier})
        otp = OTP.objects.get(identifier=identifier)

        # Verify OTP
        response = self.client.post(reverse('user-verify-otp'), {
            'identifier': identifier,
            'code': otp.code
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify we got the same user
        verified_user = User.objects.get(phone_number=identifier)
        self.assertEqual(verified_user.pk, user.pk)
        self.assertEqual(verified_user.username, "existing_user")

    def test_invalid_otp_verification(self):
        identifier = "+989123333333"
        self.client.post(reverse('user-send-otp'), {'identifier': identifier})

        response = self.client.post(reverse('user-verify-otp'), {
            'identifier': identifier,
            'code': 'wrong_code'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
