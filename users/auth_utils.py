from django.contrib.auth import get_user_model

User = get_user_model()


def should_never_lockout_staff(request):
    """
    EN:
    A callable for django-axes to prevent locking out staff members.
    Returns True if the username in the request belongs to a staff user.

    FA:
    یک تابع قابل فراخوانی برای django-axes جهت جلوگیری از مسدود شدن (lockout) اعضای کارکنان.
    اگر نام کاربری موجود در درخواست متعلق به یکی از کارکنان باشد، مقدار True برمی‌گرداند.
    """
    username = request.POST.get("username")
    if not username:
        return False

    try:
        user = User.objects.get(username=username)
        return user.is_staff
    except User.DoesNotExist:
        return False
