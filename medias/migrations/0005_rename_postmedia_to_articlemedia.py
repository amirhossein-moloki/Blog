from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("medias", "0004_alter_media_created_at_alter_media_is_active_and_more"),
        ("posts", "0007_rename_post_to_article"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="PostMedia",
            new_name="ArticleMedia",
        ),
        migrations.RenameField(
            model_name="ArticleMedia",
            old_name="post",
            new_name="article",
        ),
    ]
