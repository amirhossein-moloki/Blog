import random
import string
from django.db import IntegrityError
from .models import OTP, User

class ApplicationError(Exception):
    pass

def send_otp_service(identifier=None):
    if not identifier:
        raise ApplicationError("Identifier (email or phone number) is required.")

    otp_code = "".join(random.choices(string.digits, k=6))
    OTP.objects.filter(identifier=identifier, is_used=False).update(is_used=True)

    is_email = "@" in identifier
    user = None
    if is_email:
        user = User.objects.filter(email=identifier).first()
    else:
        user = User.objects.filter(phone_number=identifier).first()

    OTP.objects.create(
        identifier=identifier,
        code=otp_code,
        user=user
    )
    # Notifications are disabled for now as the notification app was removed.
    # In a real scenario, we would use a different service or reintegrate notifications.
    print(f"OTP for {identifier}: {otp_code}")

def verify_otp_service(identifier=None, code=None):
    if not code:
        raise ApplicationError("Code is required.")
    if not identifier:
        raise ApplicationError("Identifier (email or phone number) is required.")

    try:
        otp = OTP.objects.get(identifier=identifier, code=code, is_used=False)
    except OTP.DoesNotExist:
        raise ApplicationError("Invalid OTP.")

    if otp.is_expired:
        raise ApplicationError("OTP has expired.")

    otp.is_used = True
    otp.save()

    is_email = "@" in identifier
    if is_email:
        user = User.objects.filter(email__iexact=identifier).first()
        if user:
            created = False
        else:
            try:
                user = User.objects.create(email=identifier.lower(), username=identifier)
                created = True
            except IntegrityError:
                user = User.objects.filter(email__iexact=identifier).first()
                created = False
    else:
        user, created = User.objects.get_or_create(
            phone_number=identifier,
            defaults={"username": identifier},
        )

    if created:
        user.set_unusable_password()
        user.save()

    if not is_email and not user.is_phone_verified:
        user.is_phone_verified = True
        user.save(update_fields=["is_phone_verified"])

    return user
