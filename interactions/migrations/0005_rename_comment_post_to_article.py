from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("interactions", "0004_alter_comment_created_at_alter_comment_is_active_and_more"),
        ("posts", "0007_rename_post_to_article"),
    ]

    operations = [
        migrations.RenameField(
            model_name="comment",
            old_name="post",
            new_name="article",
        ),
    ]
