from django.db import migrations

def migrate_data(apps, schema_editor):
    Post = apps.get_model('posts', 'Post')
    PostTranslation = apps.get_model('posts', 'PostTranslation')

    for post in Post.objects.all():
        PostTranslation.objects.create(
            post=post,
            language_code='en',
            slug=post.slug,
            title=post.title,
            excerpt=post.excerpt,
            content=post.content,
            reading_time_sec=post.reading_time_sec,
            seo_title=post.seo_title,
            seo_description=post.seo_description,
        )

class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0003_create_post_translation_table'),
    ]

    operations = [
        migrations.RunPython(migrate_data),
    ]
