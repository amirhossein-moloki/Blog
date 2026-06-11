from unittest.mock import MagicMock

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from common.permissions import (
    IsAdminUserOrReadOnly,
    IsAuthorOrAdminOrReadOnly,
    IsOwnerOrReadOnly,
)

User = get_user_model()


class PermissionTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create(username="testuser")
        self.admin = User.objects.create(username="adminuser", is_staff=True)
        self.permission_author = IsAuthorOrAdminOrReadOnly()
        self.permission_owner = IsOwnerOrReadOnly()
        self.permission_admin = IsAdminUserOrReadOnly()

    def test_is_admin_user_or_readonly(self):
        request = self.factory.get("/")
        request.user = self.user
        self.assertTrue(self.permission_admin.has_permission(request, None))

        request = self.factory.post("/")
        request.user = self.user
        self.assertFalse(self.permission_admin.has_permission(request, None))

        request.user = self.admin
        self.assertTrue(self.permission_admin.has_permission(request, None))

    def test_is_owner_or_readonly_with_user_attr(self):
        obj = MagicMock()
        obj.user = self.user

        request = self.factory.get("/")
        request.user = self.user
        self.assertTrue(self.permission_owner.has_object_permission(request, None, obj))

        request = self.factory.put("/")
        request.user = self.user
        self.assertTrue(self.permission_owner.has_object_permission(request, None, obj))

    def test_is_owner_or_readonly_with_uploaded_by_attr(self):
        obj = MagicMock()
        obj.uploaded_by = self.user

        request = self.factory.put("/")
        request.user = self.user
        self.assertTrue(self.permission_owner.has_object_permission(request, None, obj))

    def test_is_owner_or_readonly_false(self):
        obj = MagicMock()
        obj.user = self.admin

        request = self.factory.put("/")
        request.user = self.user
        self.assertFalse(
            self.permission_owner.has_object_permission(request, None, obj)
        )

    def test_is_author_or_admin_or_readonly(self):
        # This permission uses apps.get_model('posts', 'AuthorProfile')
        # We need to make sure the user has an authorprofile or is staff
        request = self.factory.get("/")
        self.assertTrue(self.permission_author.has_permission(request, None))

        request = self.factory.post("/")
        request.user = None
        self.assertFalse(self.permission_author.has_permission(request, None))

        request.user = self.user
        # By default user doesn't have authorprofile
        self.assertFalse(self.permission_author.has_permission(request, None))

        from posts.models import AuthorProfile

        AuthorProfile.objects.create(user=self.user, display_name="Test Author")
        # Now has attribute 'authorprofile'
        self.assertTrue(self.permission_author.has_permission(request, None))

        request.user = self.admin
        self.assertTrue(self.permission_author.has_permission(request, None))

    def test_is_author_or_admin_or_readonly_obj(self):
        from posts.models import AuthorProfile

        author_profile = AuthorProfile.objects.create(
            user=self.user, display_name="Test Author"
        )
        obj = MagicMock()
        obj.author = author_profile

        request = self.factory.put("/")
        request.user = self.user
        self.assertTrue(
            self.permission_author.has_object_permission(request, None, obj)
        )

        request.user = self.admin
        self.assertTrue(
            self.permission_author.has_object_permission(request, None, obj)
        )

        other_user = User.objects.create(username="other")
        request.user = other_user
        self.assertFalse(
            self.permission_author.has_object_permission(request, None, obj)
        )

        request.user = self.admin
        self.assertFalse(
            self.permission_owner.has_object_permission(request, None, obj)
        )

    def test_is_owner_or_readonly_with_author_attr(self):
        author = MagicMock()
        author.user = self.user
        obj = MagicMock()
        obj.author = author

        request = self.factory.put("/")
        request.user = self.user
        self.assertTrue(self.permission_owner.has_object_permission(request, None, obj))
