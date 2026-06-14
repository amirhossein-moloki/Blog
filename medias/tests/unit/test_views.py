import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from medias.models import Media
from users.models import User


class MediaViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="mediauser", password="password")
        self.admin = User.objects.create_superuser(
            username="admin", password="password", email="admin@example.com"
        )
        self.list_url = reverse("medias:media-list")

    def test_create_media_image(self):
        self.client.force_authenticate(user=self.user)

        file = io.BytesIO()
        image = Image.new("RGB", size=(100, 100), color=(155, 0, 0))
        image.save(file, "png")
        file.name = "test.png"
        file.seek(0)

        uploaded_file = SimpleUploadedFile(
            file.name, file.read(), content_type="image/png"
        )
        data = {"file": uploaded_file, "title": "Test Image", "alt_text": "Alt text"}

        response = self.client.post(self.list_url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data["data"] if "data" in response.data else response.data
        self.assertEqual(data["title"], "Test Image")
        self.assertEqual(data["type"], "image")

    def test_create_media_file(self):
        self.client.force_authenticate(user=self.user)
        # Optimization removed, so we just check if it's saved as-is
        uploaded_file = SimpleUploadedFile(
            "test.mp4", b"hello world", content_type="video/mp4"
        )
        data = {"file": uploaded_file, "title": "Test File"}

        response = self.client.post(self.list_url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data["data"] if "data" in response.data else response.data
        self.assertEqual(data["type"], "video")

    def test_download_media(self):
        media = Media.objects.create(
            storage_key="test.txt",
            url="/media/test.txt",
            size_bytes=11,
            mime="text/plain",
            title="Test File",
            uploaded_by=self.user,
            type="file",
        )
        from django.core.files.storage import default_storage

        default_storage.save("test.txt", io.BytesIO(b"hello world"))

        url = reverse("medias:download_media", kwargs={"media_id": media.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response["Content-Disposition"], 'attachment; filename="Test File"'
        )

    def test_get_queryset_and_serializer_class(self):
        self.client.force_authenticate(user=self.admin)
        # Retrieve
        media = Media.objects.create(
            storage_key="test2.txt",
            url="/media/test2.txt",
            size_bytes=10,
            mime="text/plain",
            title="Test 2",
            uploaded_by=self.user,
            type="file",
        )
        url = reverse("medias:media-detail", kwargs={"pk": media.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # List
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class MediaServiceExtraTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="mediauser2", password="password")

    def test_create_media_video(self):
        from medias.services import create_media_from_file

        uploaded_file = SimpleUploadedFile(
            "test.mp4", b"fake video content", content_type="video/mp4"
        )
        media = create_media_from_file(uploaded_file, self.user)
        self.assertEqual(media.type, "video")
        self.assertEqual(media.mime, "video/mp4")

    def test_create_media_generic_file(self):
        from medias.services import create_media_from_file

        uploaded_file = SimpleUploadedFile(
            "test.pdf", b"fake pdf content", content_type="application/pdf"
        )
        media = create_media_from_file(uploaded_file, self.user)
        self.assertEqual(media.type, "file")
        self.assertEqual(media.mime, "application/pdf")

    def test_create_media_image_corrupt(self):
        from medias.services import create_media_from_file

        uploaded_file = SimpleUploadedFile(
            "corrupt.jpg", b"not an image", content_type="image/jpeg"
        )
        # convert_image_to_avif is removed
        media = create_media_from_file(uploaded_file, self.user)
        self.assertEqual(media.type, "image")
        self.assertIsNone(media.width)
        self.assertIsNone(media.height)
