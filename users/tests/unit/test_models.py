from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from users.models import User, OTP

class OTPModelTests(TestCase):
    def test_otp_save_sets_expires_at(self):
        otp = OTP.objects.create(identifier="test@example.com", code="123456")
        self.assertIsNotNone(otp.expires_at)
        # Should be roughly 5 minutes from now
        now = timezone.now()
        self.assertLess(otp.expires_at, now + timedelta(minutes=5, seconds=1))
        self.assertGreater(otp.expires_at, now + timedelta(minutes=4, seconds=59))

    def test_otp_is_expired(self):
        otp = OTP.objects.create(identifier="test@example.com", code="123456")
        self.assertFalse(otp.is_expired)

        otp.expires_at = timezone.now() - timedelta(seconds=1)
        otp.save()
        self.assertTrue(otp.is_expired)

class UserModelTests(TestCase):
    def test_user_str(self):
        user = User.objects.create(username="testuser", phone_number="+989123456789")
        self.assertEqual(str(user), "testuser")

    def test_user_role(self):
        from django.contrib.auth.models import Group
        user = User.objects.create(username="testuser", phone_number="+989123456789")
        group = Group.objects.create(name="Author")
        user.groups.add(group)
        self.assertEqual(user.role, ["Author"])
