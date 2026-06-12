from .models import Comment, Reaction
from .tasks import notify_author_on_new_comment


def create_comment(user, post, content, parent=None, ip=None, user_agent=""):
    """
    EN:
    Service to handle comment creation.
    Triggers a notification to the post author.

    FA:
    سرویسی برای مدیریت ایجاد نظر.
    یک اعلان برای نویسنده پست ارسال می‌کند.
    """
    comment = Comment.objects.create(
        user=user,
        post=post,
        content=content,
        parent=parent,
        ip=ip,
        user_agent=user_agent,
    )
    notify_author_on_new_comment.delay(comment.id)
    return comment


def toggle_reaction(user, content_object, reaction_type):
    """
    EN:
    Service to toggle a user reaction on a content object.
    If the reaction exists, it is removed; otherwise, it is created.

    FA:
    سرویسی برای تغییر وضعیت (toggle) واکنش کاربر روی یک شیء محتوا.
    اگر واکنش وجود داشته باشد حذف می‌شود، در غیر این صورت ایجاد می‌گردد.
    """
    from django.contrib.contenttypes.models import ContentType

    content_type = ContentType.objects.get_for_model(content_object)

    reaction, created = Reaction.objects.get_or_create(
        user=user,
        content_type=content_type,
        object_id=content_object.id,
        reaction=reaction_type,
    )

    if not created:
        reaction.delete()
        return None
    return reaction
