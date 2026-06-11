from .models import Page


def get_published_pages():
    return Page.objects.filter(status="published")
