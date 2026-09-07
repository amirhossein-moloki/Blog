import importlib
import os
from unittest import mock

from django.test import SimpleTestCase


class SettingsForwardedHeadersTestCase(SimpleTestCase):
    """Test environment variable configuration for USE_X_FORWARDED_HOST and USE_X_FORWARDED_PORT."""

    def test_default_values(self):
        """Test default values when environment variables are not set."""
        with mock.patch.dict(os.environ, {}, clear=True):
            import blog.settings as blog_settings

            importlib.reload(blog_settings)
            self.assertTrue(blog_settings.USE_X_FORWARDED_HOST)
            self.assertTrue(blog_settings.USE_X_FORWARDED_PORT)

    def test_truthy_values(self):
        """Test truthy string values ('true', '1', 't')."""
        truthy_inputs = ["true", "TRUE", "1", "t", "T"]
        for val in truthy_inputs:
            with mock.patch.dict(
                os.environ,
                {
                    "USE_X_FORWARDED_HOST": val,
                    "USE_X_FORWARDED_PORT": val,
                },
                clear=True,
            ):
                import blog.settings as blog_settings

                importlib.reload(blog_settings)
                self.assertTrue(
                    blog_settings.USE_X_FORWARDED_HOST,
                    f"Failed for USE_X_FORWARDED_HOST={val}",
                )
                self.assertTrue(
                    blog_settings.USE_X_FORWARDED_PORT,
                    f"Failed for USE_X_FORWARDED_PORT={val}",
                )

    def test_falsy_values(self):
        """Test falsy string values ('false', '0', 'f', etc.)."""
        falsy_inputs = ["false", "FALSE", "0", "f", "off", "no"]
        for val in falsy_inputs:
            with mock.patch.dict(
                os.environ,
                {
                    "USE_X_FORWARDED_HOST": val,
                    "USE_X_FORWARDED_PORT": val,
                },
                clear=True,
            ):
                import blog.settings as blog_settings

                importlib.reload(blog_settings)
                self.assertFalse(
                    blog_settings.USE_X_FORWARDED_HOST,
                    f"Failed for USE_X_FORWARDED_HOST={val}",
                )
                self.assertFalse(
                    blog_settings.USE_X_FORWARDED_PORT,
                    f"Failed for USE_X_FORWARDED_PORT={val}",
                )

    def tearDown(self):
        """Reload settings module after tests to restore original state."""
        import blog.settings as blog_settings

        importlib.reload(blog_settings)
