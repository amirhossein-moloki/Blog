from django.test import TestCase
from users.services import send_otp_service, verify_otp_service, ApplicationError
from users.models import OTP, User
from django.utils import timezone
from datetime import timedelta

class OTPServiceTest(TestCase):
    def test_full_otp_cycle(self):
        identifier = "service_test@example.com"
        send_otp_service(identifier)
        otp = OTP.objects.get(identifier=identifier)
        self.assertEqual(len(otp.code), 6)

        user = verify_otp_service(identifier, otp.code)
        self.assertEqual(user.email, identifier)
        self.assertTrue(OTP.objects.get(pk=otp.pk).is_used)

    def test_verify_otp_expired(self):
        identifier = "expired@test.com"
        send_otp_service(identifier)
        otp = OTP.objects.get(identifier=identifier)
        otp.expires_at = timezone.now() - timedelta(minutes=1)
        otp.save()

        with self.assertRaises(ApplicationError) as cm:
            verify_otp_service(identifier, otp.code)
        self.assertEqual(str(cm.exception), "OTP has expired.")
