from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("posts", "0006_galleryitem_podcastcategory_category_icon_and_more"),
        ("interactions", "0004_alter_comment_created_at_alter_comment_is_active_and_more"),
        ("medias", "0004_alter_media_created_at_alter_media_is_active_and_more"),
    ]

    operations = [
        # Rename models
        migrations.RenameModel(
            old_name="Post",
            new_name="Article",
        ),
        migrations.RenameModel(
            old_name="PostTranslation",
            new_name="ArticleTranslation",
        ),
        migrations.RenameModel(
            old_name="PostTag",
            new_name="ArticleTag",
        ),

        # Rename fields on Article
        migrations.RenameField(
            model_name="Article",
            old_name="cover_media",
            new_name="cover_image",
        ),
        migrations.RenameField(
            model_name="Article",
            old_name="related_posts",
            new_name="related_articles",
        ),

        # Rename foreign keys/fields referencing old Post
        migrations.RenameField(
            model_name="ArticleTranslation",
            old_name="post",
            new_name="article",
        ),
        migrations.RenameField(
            model_name="ArticleTag",
            old_name="post",
            new_name="article",
        ),
        migrations.RenameField(
            model_name="Revision",
            old_name="post",
            new_name="article",
        ),
    ]
