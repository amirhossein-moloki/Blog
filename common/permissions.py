from django.apps import apps
from rest_framework import permissions


class IsAuthorOrAdminOrReadOnly(permissions.BasePermission):
    """
    EN:
    Custom permission to allow read-only access to anyone,
    but only allow write operations to the author of the post or admin users.

    FA:
    سطح دسترسی سفارشی برای اجازه دسترسی فقط خواندنی به همه،
    اما اجازه عملیات نوشتنی فقط به نویسنده پست یا کاربران ادمین.
    """

    def has_permission(self, request, view):
        """
        EN: Checks if the user has general permission to access the view.
        FA: بررسی می‌کند که آیا کاربر اجازه کلی برای دسترسی به view را دارد یا خیر.
        """
        # EN: Allow all safe methods (GET, HEAD, OPTIONS)
        # FA: اجازه دادن به تمامی متدهای ایمن (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            return True

        # EN: Deny writes for unauthenticated users
        # FA: عدم اجازه نوشتن برای کاربران احراز هویت نشده
        if not request.user or not request.user.is_authenticated:
            return False

        # EN: For write methods, check if user is staff or has an author profile
        # FA: برای متدهای نوشتنی، بررسی ادمین بودن یا داشتن پروفایل نویسندگی
        if request.user.is_staff:
            return True

        AuthorProfile = apps.get_model("posts", "AuthorProfile")
        try:
            return hasattr(request.user, "authorprofile")
        except AuthorProfile.DoesNotExist:
            return False

    def has_object_permission(self, request, view, obj):
        """
        EN: Checks if the user has permission to perform the action on a specific object.
        FA: بررسی می‌کند که آیا کاربر اجازه انجام عملیات روی یک شیء خاص را دارد یا خیر.
        """
        # EN: Allow all safe methods (GET, HEAD, OPTIONS)
        # FA: اجازه دادن به تمامی متدهای ایمن (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            return True

        # EN: Allow writes if the user is an admin
        # FA: اجازه نوشتن در صورتی که کاربر ادمین باشد
        if request.user.is_staff:
            return True

        # EN: Allow writes if the user is the author of the post
        # FA: اجازه نوشتن در صورتی که کاربر نویسنده پست باشد
        return obj.author.user == request.user


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    EN:
    Custom permission to only allow owners of an object to edit it.
    Checks for 'user', 'author', or 'uploaded_by' attributes on the object.

    FA:
    سطح دسترسی سفارشی برای اینکه فقط صاحبان یک شیء بتوانند آن را ویرایش کنند.
    ویژگی‌های 'user' یا 'author' یا 'uploaded_by' را در شیء بررسی می‌کند.
    """

    def has_object_permission(self, request, view, obj):
        """
        EN: Checks if the requesting user is the owner of the object.
        FA: بررسی می‌کند که آیا کاربر درخواست‌دهنده صاحب شیء هست یا خیر.
        """
        # EN: Read permissions are allowed to any request
        # FA: دسترسی‌های خواندنی برای هر درخواستی مجاز است
        if request.method in permissions.SAFE_METHODS:
            return True

        # EN: A list of possible attribute names for the owner.
        # FA: لیستی از نام‌های احتمالی ویژگی صاحب شیء.
        owner_attributes = ["user", "author", "uploaded_by"]

        for attr in owner_attributes:
            if hasattr(obj, attr):
                owner = getattr(obj, attr)
                # EN: If the owner attribute is a direct user
                # FA: اگر ویژگی صاحب مستقیماً یک کاربر باشد
                if owner == request.user:
                    return True
                # EN: If the owner attribute is a related model (like AuthorProfile)
                # FA: اگر ویژگی صاحب یک مدل مرتبط باشد (مانند AuthorProfile)
                if hasattr(owner, "user") and owner.user == request.user:
                    return True

        return False


class IsAdminUserOrReadOnly(permissions.BasePermission):
    """
    EN:
    Allows read-only access to non-admin users, and full access to admin users.

    FA:
    اجازه دسترسی فقط خواندنی به کاربران غیر ادمین، و دسترسی کامل به کاربران ادمین.
    """

    def has_permission(self, request, view):
        """
        EN: Grants access if the method is safe or the user is staff.
        FA: اگر متد ایمن باشد یا کاربر جزو کارکنان باشد، اجازه دسترسی می‌دهد.
        """
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff
