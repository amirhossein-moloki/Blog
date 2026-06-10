from django.test import TestCase
from unittest.mock import patch
from users.services import send_otp_service, verify_otp_service, ApplicationError
from users.models import User, OTP

class OTPServiceTests(TestCase):
    def test_send_otp_service_no_identifier(self):
        with self.assertRaises(ApplicationError) as cm:
            send_otp_service(None)
        self.assertEqual(str(cm.exception), "Identifier (email or phone number) is required.")

    def test_send_otp_service_success_email(self):
        identifier = "test@example.com"
        send_otp_service(identifier)
        self.assertEqual(OTP.objects.filter(identifier=identifier).count(), 1)
        otp = OTP.objects.get(identifier=identifier)
        self.assertEqual(len(otp.code), 6)
        self.assertFalse(otp.is_used)

    def test_send_otp_service_success_phone(self):
        identifier = "+989123456780"
        User.objects.create(username="phoneuser", phone_number=identifier)
        send_otp_service(identifier)
        self.assertEqual(OTP.objects.filter(identifier=identifier).count(), 1)
        otp = OTP.objects.get(identifier=identifier)
        self.assertIsNotNone(otp.user)

    def test_verify_otp_service_no_code(self):
        with self.assertRaises(ApplicationError) as cm:
            verify_otp_service(identifier="test@example.com", code=None)
        self.assertEqual(str(cm.exception), "Code is required.")

    def test_verify_otp_service_invalid_otp(self):
        with self.assertRaises(ApplicationError) as cm:
            verify_otp_service(identifier="test@example.com", code="000000")
        self.assertEqual(str(cm.exception), "Invalid OTP.")

    def test_verify_otp_service_expired_otp(self):
        identifier = "test@example.com"
        code = "123456"
        otp = OTP.objects.create(identifier=identifier, code=code)
        otp.expires_at = timezone_now_minus_one_minute()
        otp.save()

        with patch('django.utils.timezone.now', return_value=timezone_now_plus_one_hour()):
             with self.assertRaises(ApplicationError) as cm:
                verify_otp_service(identifier=identifier, code=code)
             self.assertEqual(str(cm.exception), "OTP has expired.")

    def test_verify_otp_service_success_new_user_email(self):
        identifier = "NewUser@Example.com"
        code = "123456"
        OTP.objects.create(identifier=identifier, code=code)

        user = verify_otp_service(identifier=identifier, code=code)
        self.assertIsInstance(user, User)
        self.assertEqual(user.email, identifier.lower())
        self.assertTrue(OTP.objects.get(identifier=identifier, code=code).is_used)

    def test_verify_otp_service_success_existing_user_email(self):
        identifier = "existing@example.com"
        User.objects.create(username=identifier, email=identifier, phone_number="+989120000100")
        code = "123456"
        OTP.objects.create(identifier=identifier, code=code)

        user = verify_otp_service(identifier=identifier, code=code)
        self.assertEqual(user.email, identifier)

    def test_verify_otp_service_success_existing_user_phone(self):
        phone = "+989123456789"
        user = User.objects.create(username="existing", phone_number=phone)
        code = "123456"
        OTP.objects.create(identifier=phone, code=code)

        verified_user = verify_otp_service(identifier=phone, code=code)
        self.assertEqual(verified_user, user)
        self.assertTrue(verified_user.is_phone_verified)

    def test_verify_otp_service_success_new_user_phone(self):
        phone = "+989123456777"
        code = "123456"
        OTP.objects.create(identifier=phone, code=code)

        user = verify_otp_service(identifier=phone, code=code)
        self.assertEqual(str(user.phone_number), phone)
        self.assertTrue(user.is_phone_verified)

    def test_verify_otp_service_email_integrity_error(self):
        from django.db import IntegrityError
        identifier = "race@example.com"
        code = "123456"
        OTP.objects.create(identifier=identifier, code=code)

        user = User.objects.create(username="race", email=identifier, phone_number="+989120000555")

        with patch('users.models.User.objects.create', side_effect=IntegrityError):
            verified_user = verify_otp_service(identifier=identifier, code=code)
            self.assertEqual(verified_user, user)

def timezone_now_minus_one_minute():
    from django.utils import timezone
    from datetime import timedelta
    return timezone.now() - timedelta(minutes=1)

def timezone_now_plus_one_hour():
    from django.utils import timezone
    from datetime import timedelta
    return timezone.now() + timedelta(hours=1)
