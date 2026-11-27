from django.urls import reverse
from rest_framework import status

from posts.blog_tests.base import BaseAPITestCase
from posts.factories import CategoryFactory, TagFactory
from posts.models import Category, Tag


class CategoryAPITest(BaseAPITestCase):
    def test_create_category(self):
        self._authenticate_as_staff()
        url = reverse("posts:category-list")
        data = {"name": "New Category", "slug": "new-category"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Category.objects.filter(slug="new-category").exists())

    def test_create_nested_category(self):
        self._authenticate_as_staff()
        parent_category = CategoryFactory()
        url = reverse("posts:category-list")
        data = {
            "name": "Sub Category",
            "slug": "sub-category",
            "parent": parent_category.id,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Category.objects.filter(
                slug="sub-category", parent=parent_category
            ).exists()
        )

    def test_list_categories(self):
        CategoryFactory.create_batch(3)
        url = reverse("posts:category-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_category_persian_auto_unique_slug_and_lookup(self):
        self._authenticate_as_staff()
        list_url = reverse("posts:category-list")

        r1 = self.client.post(list_url, {"name": "تکنولوژی روز"}, format="json")
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r1.data["slug"], "تکنولوژی-روز")

        r2 = self.client.post(
            list_url, {"name": "تکنولوژی روز", "slug": ""}, format="json"
        )
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r2.data["slug"], "تکنولوژی-روز-2")

        r3 = self.client.post(list_url, {"name": "تکنولوژی روز"}, format="json")
        self.assertEqual(r3.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r3.data["slug"], "تکنولوژی-روز-3")

        r_explicit = self.client.post(
            list_url,
            {"name": "دسته ویژه", "slug": "گجت-هوشمند"},
            format="json",
        )
        self.assertEqual(r_explicit.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r_explicit.data["slug"], "گجت-هوشمند")

        detail_by_slug = reverse(
            "posts:category-detail", kwargs={"pk": "تکنولوژی-روز"}
        )
        detail_res = self.client.get(detail_by_slug)
        self.assertEqual(detail_res.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_res.data["id"], r1.data["id"])

        patch_res = self.client.patch(
            detail_by_slug, {"name": "تکنولوژی جدید"}, format="json"
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data["name"], "تکنولوژی جدید")
        self.assertEqual(patch_res.data["slug"], "تکنولوژی-روز")

        detail_by_pk = reverse("posts:category-detail", kwargs={"pk": r1.data["id"]})
        self.assertEqual(
            self.client.get(detail_by_pk).status_code, status.HTTP_200_OK
        )

        del_res = self.client.delete(detail_by_slug)
        self.assertEqual(del_res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(pk=r1.data["id"]).exists())


class TagAPITest(BaseAPITestCase):
    def test_create_tag(self):
        self._authenticate_as_staff()
        url = reverse("posts:tag-list")
        data = {"name": "New Tag", "slug": "new-tag"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Tag.objects.filter(slug="new-tag").exists())

    def test_list_tags(self):
        TagFactory.create_batch(5)
        url = reverse("posts:tag-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)

    def test_tag_list_returns_id(self):
        """
        Ensure the tag list API endpoint returns the tag ID.
        """
        self._authenticate_as_staff()
        tag = TagFactory()
        url = reverse("posts:tag-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("id", response.data[0])
        self.assertEqual(response.data[0]["id"], tag.id)

    def test_tag_detail_returns_id(self):
        """
        Ensure the tag detail API endpoint returns the tag ID.
        """
        self._authenticate_as_staff()
        tag = TagFactory()
        url = reverse("posts:tag-detail", kwargs={"pk": tag.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["id"], tag.id)

    def test_tag_persian_auto_unique_slug_and_lookup(self):
        self._authenticate_as_staff()
        list_url = reverse("posts:tag-list")

        r1 = self.client.post(list_url, {"name": "هوش مصنوعی"}, format="json")
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r1.data["slug"], "هوش-مصنوعی")

        r2 = self.client.post(
            list_url, {"name": "هوش مصنوعی", "slug": ""}, format="json"
        )
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r2.data["slug"], "هوش-مصنوعی-2")

        r3 = self.client.post(list_url, {"name": "هوش مصنوعی"}, format="json")
        self.assertEqual(r3.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r3.data["slug"], "هوش-مصنوعی-3")

        r_explicit = self.client.post(
            list_url,
            {"name": "برچسب خاص", "slug": "تگ-فارسی"},
            format="json",
        )
        self.assertEqual(r_explicit.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r_explicit.data["slug"], "تگ-فارسی")

        detail_by_slug = reverse("posts:tag-detail", kwargs={"pk": "تگ-فارسی"})
        detail_res = self.client.get(detail_by_slug)
        self.assertEqual(detail_res.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_res.data["id"], r_explicit.data["id"])

        patch_res = self.client.patch(
            detail_by_slug, {"name": "برچسب ویرایش‌شده"}, format="json"
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data["slug"], "تگ-فارسی")

        detail_by_pk = reverse(
            "posts:tag-detail", kwargs={"pk": r_explicit.data["id"]}
        )
        self.assertEqual(
            self.client.get(detail_by_pk).status_code, status.HTTP_200_OK
        )

        del_res = self.client.delete(detail_by_slug)
        self.assertEqual(del_res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Tag.objects.filter(pk=r_explicit.data["id"]).exists())
