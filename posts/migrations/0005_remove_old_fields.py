from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0004_migrate_post_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='post',
            name='slug',
        ),
        migrations.RemoveField(
            model_name='post',
            name='title',
        ),
        migrations.RemoveField(
            model_name='post',
            name='excerpt',
        ),
        migrations.RemoveField(
            model_name='post',
            name='content',
        ),
        migrations.RemoveField(
            model_name='post',
            name='reading_time_sec',
        ),
        migrations.RemoveField(
            model_name='post',
            name='seo_title',
        ),
        migrations.RemoveField(
            model_name='post',
            name='seo_description',
        ),
    ]
