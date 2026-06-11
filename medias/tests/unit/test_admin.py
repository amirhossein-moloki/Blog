from django.contrib.admin.sites import AdminSite
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase

from medias.admin import MediaAdmin
from medias.models import Media
from users.models import User


class MediaAdminTests(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.user = User.objects.create_superuser(
            username="admin3", password="password", email="admin3@example.com"
        )
        self.media = Media.objects.create(
            storage_key="test.txt",
            url="/media/test.txt",
            size_bytes=10,
            mime="text/plain",
            title="Test",
            uploaded_by=self.user,
            type="file",
        )
        self.admin = MediaAdmin(Media, self.site)

    def test_get_created_at_jalali(self):
        self.assertIsNotNone(self.admin.get_created_at_jalali(self.media))
        self.media.created_at = None
        self.assertIsNone(self.admin.get_created_at_jalali(self.media))

    def test_download_link(self):
        link = self.admin.download_link(self.media)
        self.assertIn("href", link)
        self.assertIn("download", link.lower())

        unsaved_media = Media()
        self.assertEqual(self.admin.download_link(unsaved_media), "N/A")

    def test_get_readonly_fields(self):
        factory = RequestFactory()
        request = factory.get("/")
        request.user = self.user

        # Edit mode
        readonly = self.admin.get_readonly_fields(request, self.media)
        self.assertIn("storage_key", readonly)

        # Add mode
        readonly = self.admin.get_readonly_fields(request, None)
        self.assertIn("storage_key", readonly)

    def test_save_model(self):
        factory = RequestFactory()
        request = factory.get("/")
        request.user = self.user

        import io

        from PIL import Image

        file = io.BytesIO()
        image = Image.new("RGB", size=(10, 10), color=(155, 0, 0))
        image.save(file, "jpeg")
        file.name = "test.jpg"
        file.seek(0)

        new_media = Media(title="Unsaved")

        # Mock form cleaned_data
        class MockForm:
            cleaned_data = {
                "file": SimpleUploadedFile(
                    file.name, file.read(), content_type="image/jpeg"
                ),
                "alt_text": "alt",
                "title": "new title",
            }

        # To avoid actual saving and deletion of files in create_media_from_file
        # we can just test the pk assignment
        self.admin.save_model(request, new_media, MockForm(), change=False)
        self.assertEqual(new_media.uploaded_by, self.user)
        self.assertTrue(new_media.pk)
