from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from users.models import User

class AuthFlowIntegrationTest(APITestCase):
    def test_full_auth_flow_new_user(self):
        # 1. Signup
        signup_url = reverse('user-list')
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'Password123!',
            'password_confirm': 'Password123!',
            'first_name': 'New',
            'last_name': 'User'
        }
        response = self.client.post(signup_url, data)
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Signup failed: {response.data}")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify user was created
        self.assertTrue(User.objects.filter(username='newuser').exists())
        user = User.objects.get(username='newuser')

        # 2. Login
        login_url = reverse('token_obtain_pair')
        response = self.client.post(login_url, {
            'username': 'newuser',
            'password': 'Password123!'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        token_data = response.data.get('data', response.data)
        self.assertIn('access', token_data)
        self.assertIn('refresh', token_data)

        access_token = token_data['access']

        # 3. Access 'me' endpoint with token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        me_url = reverse('user-me')
        response = self.client.get(me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user_data = response.data.get('data', response.data)
        self.assertEqual(user_data['username'], user.username)

    def test_invalid_login(self):
        User.objects.create_user(username='testuser', password='Password123!')
        login_url = reverse('token_obtain_pair')
        response = self.client.post(login_url, {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
