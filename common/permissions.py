from django.apps import apps
from rest_framework import permissions


class IsAuthorOrAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow read-only access to anyone,
    but only allow write operations to the author of the post or admin users.
    """

    def has_permission(self, request, view):
        # Allow all safe methods (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            return True

        # Deny writes for unauthenticated users
        if not request.user or not request.user.is_authenticated:
            return False

        # For write methods, check if user is staff or has an author profile
        if request.user.is_staff:
            return True

        AuthorProfile = apps.get_model("posts", "AuthorProfile")
        try:
            return hasattr(request.user, "authorprofile")
        except AuthorProfile.DoesNotExist:
            return False

    def has_object_permission(self, request, view, obj):
        # Allow all safe methods (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            return True

        # Allow writes if the user is an admin
        if request.user.is_staff:
            return True

        # Allow writes if the user is the author of the post
        return obj.author.user == request.user


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    Checks for 'user', 'author', or 'uploaded_by' attributes on the object.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # A list of possible attribute names for the owner.
        owner_attributes = ["user", "author", "uploaded_by"]

        for attr in owner_attributes:
            if hasattr(obj, attr):
                owner = getattr(obj, attr)
                # If the owner attribute is a direct user
                if owner == request.user:
                    return True
                # If the owner attribute is a related model (like AuthorProfile)
                if hasattr(owner, "user") and owner.user == request.user:
                    return True

        return False


class IsAdminUserOrReadOnly(permissions.BasePermission):
    """
    Allows read-only access to non-admin users, and full access to admin users.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff
