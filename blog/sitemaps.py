from django.contrib.sitemaps import Sitemap
from django.utils import timezone

from posts.models import Article


class ArticleSitemap(Sitemap):
    """
    EN: Sitemap generator for published public blog articles.
    FA: تولیدکننده نقشه سایت (Sitemap) برای مقاله‌های منتشر شده و عمومی بلاگ.
    """

    changefreq = "weekly"
    priority = 0.9

    def items(self):
        """
        EN: Returns published public articles that have an active translation slug.
        FA: لیستی از مقاله‌های منتشر شده عمومی دارای اسلاگ معتبر را بازمی‌گرداند.
        """
        articles = (
            Article.objects.published()
            .with_translations("fa")
            .filter(visibility="public", published_at__lte=timezone.now())
        )
        return [
            article
            for article in articles
            if article.translation and getattr(article.translation, "slug", None)
        ]

    def lastmod(self, obj):
        """
        EN: Returns the last modification or publication date of an article.
        FA: تاریخ آخرین تغییر یا انتشار یک مقاله را بازمی‌گرداند.
        """
        return obj.updated_at or obj.published_at

    def location(self, obj):
        """
        EN: Returns the canonical article path on the frontend site.
        FA: مسیر کانونیکال مقاله در سایت اصلی را بازمی‌گرداند.
        """
        trans = obj.translation
        return f"/blog/{trans.slug}"


class StaticViewSitemap(Sitemap):
    """
    EN: Sitemap generator for public blog listing route.
    FA: تولیدکننده نقشه سایت برای صفحه اصلی وبلاگ.
    """

    priority = 0.5
    changefreq = "daily"

    def items(self):
        return ["/blog"]

    def location(self, item):
        return item
