from django.test import SimpleTestCase
from django.urls import reverse


class SwaggerSchemaViewTests(SimpleTestCase):
    """
    EN: Tests verifying OpenAPI documentation endpoints and schema URLs.
    FA: تست‌های اعتبارسنجی اندپوینت‌های مستندات OpenAPI و مسیرهای اسکیما.
    """

    def test_swagger_ui_schema_url(self):
        url = reverse("swagger-ui")
        response = self.client.get(url, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'url: "/blog/api/schema/"')

    def test_redoc_schema_url(self):
        url = reverse("redoc")
        response = self.client.get(url, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'spec-url="/blog/api/schema/"')
