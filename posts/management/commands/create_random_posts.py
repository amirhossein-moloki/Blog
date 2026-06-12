import random

import requests
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from faker import Faker

from medias.models import Media
from posts.models import AuthorProfile, Category, Post, Tag

User = get_user_model()


class Command(BaseCommand):
    """
    EN:
    Management command to generate random posts using the Faker library.
    Useful for populating the database during development and testing.

    FA:
    دستور مدیریتی برای تولید پست‌های تصادفی با استفاده از کتابخانه Faker.
    مفید برای پر کردن پایگاه داده در طول توسعه و تست.
    """

    help = "Creates a specified number of random posts for testing and development."

    def add_arguments(self, parser):
        """
        EN: Defines the 'count' argument to specify how many posts to create.
        FA: آرگومان 'count' را برای مشخص کردن تعداد پست‌های ایجاد شونده تعریف می‌کند.
        """
        parser.add_argument(
            "count", type=int, help="The number of random posts to create."
        )

    def handle(self, *args, **options):
        """
        EN: Main logic to create random posts along with necessary dependencies (users, categories, tags).
        FA: منطق اصلی برای ایجاد پست‌های تصادفی به همراه نیازمندی‌های لازم (کاربران، دسته‌بندی‌ها، برچسب‌ها).
        """
        count = options["count"]
        fake = Faker()

        # EN: Check if any users exist, create one if not
        # FA: بررسی وجود کاربر، و ایجاد یک کاربر در صورت عدم وجود
        if not User.objects.exists():
            default_user = User.objects.create_user(
                username="defaultuser", password="password", email=fake.email()
            )
            # EN: The AuthorProfile is created by a signal, so we get or create it.
            # FA: پروفایل نویسندگی توسط سیگنال ایجاد می‌شود، بنابراین آن را دریافت یا ایجاد می‌کنیم.
            AuthorProfile.objects.get_or_create(
                user=default_user,
                defaults={
                    "display_name": default_user.username,
                    "bio": fake.paragraph(nb_sentences=3),
                },
            )
            self.stdout.write(
                self.style.SUCCESS("No users found. Created a default user.")
            )

        # EN: Get authors, categories, and tags
        # FA: دریافت نویسندگان، دسته‌بندی‌ها و برچسب‌ها
        authors = list(AuthorProfile.objects.all())
        if not authors:
            self.stderr.write(
                self.style.ERROR("No author profiles found. Create some first.")
            )
            return

        categories = list(Category.objects.all())
        if not categories:
            for i in range(5):
                Category.objects.create(name=f"Category {i}", slug=f"category-{i}")
            categories = list(Category.objects.all())
            self.stdout.write(
                self.style.SUCCESS("No categories found. Created 5 default categories.")
            )

        tags = list(Tag.objects.all())
        if not tags:
            for i in range(10):
                Tag.objects.create(name=f"Tag {i}", slug=f"tag-{i}")
            tags = list(Tag.objects.all())
            self.stdout.write(
                self.style.SUCCESS("No tags found. Created 10 default tags.")
            )

        for i in range(count):
            # EN: Create Media instances for cover and OG image
            # FA: ایجاد نمونه‌های رسانه برای کاور و تصویر OG
            cover_media = self._create_dummy_media(fake)
            og_image = self._create_dummy_media(fake)

            post = Post.objects.create(
                title=fake.sentence(nb_words=6),
                slug=f"{fake.slug()}-{i}",
                excerpt=fake.paragraph(nb_sentences=2),
                content=" ".join(fake.paragraphs(nb=5)),
                status=random.choice(["draft", "published"]),
                author=random.choice(authors),
                category=random.choice(categories),
                cover_media=cover_media,
                og_image=og_image,
            )
            post.tags.set(random.sample(tags, k=random.randint(1, 4)))

        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {count} random posts.")
        )

    def _create_dummy_media(self, fake):
        """
        EN: Downloads a placeholder image and creates a Media object.
        FA: یک تصویر جایگزین را دانلود کرده و یک شیء رسانه ایجاد می‌کند.
        """
        try:
            response = requests.get(
                "https://via.placeholder.com/800x600.png/007bff/FFFFFF?text=Image"
            )
            response.raise_for_status()  # Raise an exception for bad status codes

            file_name = f"{fake.slug()}.png"
            media = Media(
                title=file_name,
                type="image",
                mime="image/png",
            )
            media.storage_key = ContentFile(response.content, name=file_name)
            media.save()
            return media

        except requests.exceptions.RequestException as e:
            self.stderr.write(self.style.ERROR(f"Failed to download image: {e}"))
            return None
