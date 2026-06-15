from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User
from users.permissions import IsOwnerOrAdmin, IsOwnerOrReadOnly


class UserViewSetTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="password", email="admin@example.com"
        )
        self.user1 = User.objects.create_user(
            username="user1", password="password", email="user1@example.com"
        )
        self.user2 = User.objects.create_user(
            username="user2", password="password", email="user2@example.com"
        )
        self.list_url = reverse("user-list")
        self.me_url = reverse("user-me")

    def test_list_users_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check if it is already wrapped or not.
        if isinstance(response.data, list):
            data = response.data
        else:
            data = response.data["data"]
        self.assertEqual(len(data), 3)

    def test_list_users_regular_user(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if isinstance(response.data, list):
            data = response.data
        else:
            data = response.data["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["username"], "user1")

    def test_retrieve_user_self(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse("user-detail", kwargs={"pk": self.user1.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"] if "data" in response.data else response.data
        self.assertEqual(data["username"], "user1")

    def test_retrieve_user_other_by_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("user-detail", kwargs={"pk": self.user1.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"] if "data" in response.data else response.data
        self.assertEqual(data["username"], "user1")

    def test_retrieve_user_other_by_regular_user(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse("user-detail", kwargs={"pk": self.user2.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_me_endpoint(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"] if "data" in response.data else response.data
        self.assertEqual(data["username"], "user1")

    def test_create_user_success(self):
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "Password123!",
            "password_confirm": "Password123!",
            "first_name": "New",
            "last_name": "User",
        }
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_create_user_passwords_mismatch(self):
        data = {
            "username": "newuser2",
            "email": "new2@example.com",
            "password": "Password123!",
            "password_confirm": "Different123!",
        }
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_custom_token_obtain_pair_view_invalid_token(self):
        from rest_framework_simplejwt.exceptions import TokenError

        url = reverse("admin-login")
        with patch(
            "users.views.CustomTokenObtainPairView.get_serializer"
        ) as mock_get_serializer:
            mock_serializer = MagicMock()
            mock_serializer.is_valid.side_effect = TokenError("Custom token error")
            mock_get_serializer.return_value = mock_serializer
            response = self.client.post(
                url, {"username": "admin", "password": "password"}
            )
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_user_self(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse("user-detail", kwargs={"pk": self.user1.pk})
        data = {"first_name": "Updated"}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.first_name, "Updated")

    def test_update_user_strip_profile_picture_if_not_file(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse("user-detail", kwargs={"pk": self.user1.pk})
        # Sending profile_picture as a string should be stripped
        data = {
            "profile_picture": "http://example.com/image.jpg",
            "first_name": "Stripped",
        }
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.first_name, "Stripped")
        self.assertFalse(bool(self.user1.profile_picture))

    def test_update_user_with_real_profile_picture(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse("user-detail", kwargs={"pk": self.user1.pk})

        import io

        from PIL import Image

        file = io.BytesIO()
        image = Image.new("RGBA", size=(100, 100), color=(155, 0, 0))
        image.save(file, "png")
        file.name = "test.png"
        file.seek(0)

        uploaded_image = SimpleUploadedFile(
            file.name, file.read(), content_type="image/png"
        )
        data = {"profile_picture": uploaded_image}
        response = self.client.patch(url, data, format="multipart")
        if response.status_code != status.HTTP_200_OK:
            print(f"Update failed: {response.data}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user1.refresh_from_db()
        self.assertTrue(bool(self.user1.profile_picture))

    def test_delete_user_self(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse("user-detail", kwargs={"pk": self.user1.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(pk=self.user1.pk).exists())


class PermissionTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.other_user = User.objects.create_user(
            username="otheruser", password="password"
        )
        self.admin = User.objects.create_superuser(
            username="admin", password="password", email="admin@example.com"
        )

    def test_is_owner_or_read_only(self):
        perm = IsOwnerOrReadOnly()
        view = MagicMock()
        request = MagicMock()
        request.user = self.user
        request.method = "PUT"

        # Test User model itself
        self.assertTrue(perm.has_object_permission(request, view, self.user))
        self.assertFalse(perm.has_object_permission(request, view, self.other_user))

        request.method = "GET"
        self.assertTrue(perm.has_object_permission(request, view, self.other_user))

        # Test other attributes
        request.method = "PUT"
        obj1 = MagicMock()
        obj1.user = self.user
        self.assertTrue(perm.has_object_permission(request, view, obj1))

        obj2 = MagicMock(spec=["author"])
        obj2.author.user = self.user
        self.assertTrue(perm.has_object_permission(request, view, obj2))

        obj3 = MagicMock(spec=["uploaded_by"])
        obj3.uploaded_by = self.user
        self.assertTrue(perm.has_object_permission(request, view, obj3))

        # Test false cases
        request.user = self.other_user
        self.assertFalse(perm.has_object_permission(request, view, obj1))
        self.assertFalse(perm.has_object_permission(request, view, obj2))
        self.assertFalse(perm.has_object_permission(request, view, obj3))

        obj4 = MagicMock(spec=[])
        self.assertFalse(perm.has_object_permission(request, view, obj4))

    def test_is_owner_or_admin(self):
        from users.permissions import IsAdminUser

        admin_perm = IsAdminUser()
        view = MagicMock()
        request = MagicMock()
        request.user = self.admin
        self.assertTrue(admin_perm.has_permission(request, view))
        request.user = self.user
        self.assertFalse(admin_perm.has_permission(request, view))

        perm = IsOwnerOrAdmin()
        request.user = self.user
        request.method = "PUT"

        # Admin bypass
        admin_request = MagicMock()
        admin_request.user = self.admin
        obj = MagicMock()
        obj.user = self.other_user
        self.assertTrue(perm.has_object_permission(admin_request, view, obj))

        # User model
        user_obj = self.user
        # We need to mock the type name because of the check in permissions.py
        with patch("users.permissions.type") as mock_type:
            mock_type.return_value.__name__ = "User"
            self.assertTrue(perm.has_object_permission(request, view, user_obj))

        # Direct user ownership
        obj = MagicMock()
        obj.user = self.user
        self.assertTrue(perm.has_object_permission(request, view, obj))

        # Author attribute
        obj = MagicMock()
        obj.author.user = self.user
        self.assertTrue(perm.has_object_permission(request, view, obj))

        # Uploaded_by attribute
        obj = MagicMock()
        obj.uploaded_by = self.user
        self.assertTrue(perm.has_object_permission(request, view, obj))

        # False case
        obj = MagicMock(spec=[])
        self.assertFalse(perm.has_object_permission(request, view, obj))
