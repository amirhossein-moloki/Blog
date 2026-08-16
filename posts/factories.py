import factory
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from faker import Faker

from interactions.models import Comment, Reaction
from medias.models import Media
from posts.models import (
    Article,
    AuthorProfile,
    Category,
    GalleryItem,
    Podcast,
    PodcastCategory,
    Revision,
    Series,
    Tag,
)

fake = Faker()
User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("username",)

    username = factory.LazyAttribute(lambda _: fake.user_name())
    email = factory.LazyAttribute(lambda _: fake.email())
    first_name = factory.LazyAttribute(lambda _: fake.first_name())
    last_name = factory.LazyAttribute(lambda _: fake.last_name())
    is_staff = False


class AuthorProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AuthorProfile
        django_get_or_create = ("user",)

    user = factory.SubFactory(UserFactory)
    display_name = factory.LazyAttribute(
        lambda o: o.user.get_full_name() or o.user.username
    )
    bio = factory.LazyAttribute(lambda _: fake.paragraph())


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.LazyAttribute(lambda _: fake.word())
    slug = factory.Sequence(lambda n: f"{fake.slug()}-{n}")
    description = factory.LazyAttribute(lambda _: fake.sentence())


class PodcastCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PodcastCategory

    title = factory.LazyAttribute(lambda _: fake.word())
    slug = factory.Sequence(lambda n: f"podcast-cat-{n}")
    icon = factory.SubFactory("posts.factories.MediaFactory")


class PodcastFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Podcast

    title = factory.LazyAttribute(lambda _: fake.sentence())
    slug = factory.Sequence(lambda n: f"podcast-{n}")
    category = factory.SubFactory(PodcastCategoryFactory)
    episode_number = factory.Sequence(lambda n: n + 1)
    cover_image = factory.SubFactory("posts.factories.MediaFactory")
    media_type = "audio"
    duration = 45
    published_date = factory.LazyAttribute(lambda _: timezone.now())
    view_count = 0


class GalleryItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GalleryItem

    image = factory.SubFactory("posts.factories.MediaFactory")
    caption = factory.LazyAttribute(lambda _: fake.sentence())
    order = factory.Sequence(lambda n: n)


class SeriesFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Series

    title = factory.LazyAttribute(lambda _: fake.sentence())
    slug = factory.LazyAttribute(lambda o: fake.slug(o.title))
    description = factory.LazyAttribute(lambda _: fake.paragraph())


class ArticleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Article

    status = "published"
    visibility = "public"
    published_at = factory.LazyAttribute(
        lambda o: timezone.now() if o.status == "published" else None
    )
    author = factory.SubFactory(AuthorProfileFactory)
    category = factory.SubFactory(CategoryFactory)

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for tag in extracted:
                self.tags.add(tag)
        else:
            self.tags.add(TagFactory())

    @factory.post_generation
    def translation(self, create, extracted, **kwargs):
        if not create:
            return

        from posts.models import ArticleTranslation

        ArticleTranslation.objects.create(
            article=self,
            language_code=kwargs.get("language_code", "en"),
            title=kwargs.get("title", fake.sentence()),
            slug=kwargs.get("slug", f"{fake.slug()}-{self.id}"),
            excerpt=kwargs.get("excerpt", fake.paragraph()),
            content=kwargs.get("content", fake.text()),
        )


class CommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Comment

    article = factory.SubFactory(ArticleFactory)
    user = factory.SubFactory(UserFactory)
    content = factory.LazyAttribute(lambda _: fake.paragraph())
    status = "approved"


class MediaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Media

    file = factory.LazyFunction(
        lambda: SimpleUploadedFile(
            name=fake.file_name(category="image", extension="jpg"),
            content=b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b",  # A tiny valid GIF
            content_type="image/jpeg",
        )
    )
    uploaded_by = factory.SubFactory(UserFactory)
    alt_text = factory.Faker("sentence")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        uploaded_file = kwargs.pop("file")
        # Use a simplified name for the file to avoid issues with paths in storage_key
        simplified_name = fake.file_name(category="image", extension="jpg")
        storage_key = default_storage.save(simplified_name, uploaded_file)

        kwargs["storage_key"] = storage_key
        kwargs["url"] = default_storage.url(storage_key)
        kwargs["mime"] = uploaded_file.content_type
        kwargs["type"] = "image"
        kwargs["size_bytes"] = uploaded_file.size
        kwargs["title"] = uploaded_file.name

        return super()._create(model_class, *args, **kwargs)


class RevisionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Revision

    article = factory.SubFactory(ArticleFactory)
    editor = factory.SubFactory(UserFactory)
    title = factory.LazyAttribute(lambda o: o.article.translation.title)
    content = factory.LazyAttribute(lambda o: o.article.translation.content)
    excerpt = factory.LazyAttribute(lambda o: o.article.translation.excerpt)
    change_note = factory.LazyAttribute(lambda _: fake.sentence())


class ReactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Reaction

    user = factory.SubFactory(UserFactory)
    reaction = "like"
    content_type = factory.LazyAttribute(
        lambda o: ContentType.objects.get_for_model(o.content_object)
    )
    object_id = factory.SelfAttribute("content_object.id")
    content_object = factory.SubFactory(ArticleFactory)


class TagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tag

    name = factory.LazyAttribute(lambda _: fake.word())
    slug = factory.Sequence(lambda n: f"{fake.slug()}-{n}")
    description = factory.LazyAttribute(lambda _: fake.sentence())
