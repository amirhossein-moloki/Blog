from .models import Menu


def get_menu_by_location(location):
    return (
        Menu.objects.filter(location=location).prefetch_related("menuitem_set").first()
    )
