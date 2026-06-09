from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from datetime import datetime

from posts.models import Post


class PostSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Post.objects.published()

    def lastmod(self, obj):
        return obj.published_at

    def location(self, obj):
        return f"/posts/{obj.slug}"


class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = "daily"

    def items(self):
        return [
            "/",
            "/about",
            "/register/login",
            "/register/signup",
            "/user-dashboard/",
        ]

    def lastmod(self, item):
        return datetime.now()

    def location(self, item):
        return item
