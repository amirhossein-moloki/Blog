from django.contrib.auth import get_user_model
from rest_framework import permissions

User = get_user_model()


class IsAdminUser(permissions.BasePermission):
    """
    EN:
    Custom permission to only allow admin users (staff) to access a view.

    FA:
    سطح دسترسی سفارشی برای اینکه فقط کاربران ادمین (staff) اجازه دسترسی داشته باشند.
    """

    def has_permission(self, request, view):
        """
        EN: Returns True if the user is staff.
        FA: اگر کاربر ادمین باشد، مقدار True را برمی‌گرداند.
        """
        return bool(request.user and request.user.is_staff)


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    EN:
    Custom permission to only allow owners of an object to edit it.
    Checks for various potential owner attributes like 'user', 'author', or 'uploaded_by'.

    FA:
    سطح دسترسی سفارشی برای اینکه فقط صاحبان یک شیء بتوانند آن را ویرایش کنند.
    ویژگی‌های مختلف صاحب شیء مانند 'user'، 'author' یا 'uploaded_by' را بررسی می‌کند.
    """

    def has_object_permission(self, request, view, obj):
        """
        EN: Grants access for safe methods or if the user is the owner.
        FA: اجازه دسترسی برای متدهای ایمن یا در صورتی که کاربر صاحب شیء باشد را صادر می‌کند.
        """
        if request.method in permissions.SAFE_METHODS:
            return True
        if hasattr(obj, "user"):
            return obj.user == request.user
        if hasattr(obj, "author"):
            return obj.author.user == request.user
        if hasattr(obj, "uploaded_by"):
            return obj.uploaded_by == request.user
        # EN: For User model itself
        # FA: برای خود مدل کاربر (User)
        if hasattr(obj, "id"):
            return obj.id == request.user.id
        return False


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    EN:
    Custom permission to allow owners of an object or admin users to edit it.
    Handles multiple ownership scenarios across different apps.

    FA:
    سطح دسترسی سفارشی برای اجازه دادن به صاحبان یک شیء یا کاربران ادمین جهت ویرایش آن.
    سناریوهای مختلف مالکیت را در اپلیکیشن‌های مختلف مدیریت می‌کند.
    """

    def has_object_permission(self, request, view, obj):
        """
        EN: Grants access for safe methods, for staff, or for the owner.
        FA: اجازه دسترسی برای متدهای ایمن، برای ادمین‌ها یا برای صاحب شیء را صادر می‌کند.
        """
        if request.method in permissions.SAFE_METHODS:
            return True

        if request.user and request.user.is_staff:
            return True

        # EN: Direct user ownership
        # FA: مالکیت مستقیم کاربر
        if hasattr(obj, "user") and obj.user == request.user:
            return True

        # EN: Ownership via author profile
        # FA: مالکیت از طریق پروفایل نویسندگی
        if (
            hasattr(obj, "author")
            and hasattr(obj.author, "user")
            and obj.author.user == request.user
        ):
            return True

        # EN: Ownership for uploaded files
        # FA: مالکیت برای فایل‌های آپلود شده
        if hasattr(obj, "uploaded_by") and obj.uploaded_by == request.user:
            return True

        # EN: Ownership for the User model itself
        # FA: مالکیت برای خود مدل کاربر (User)
        if isinstance(obj, User) and obj.id == request.user.id:
            return True

        return False
