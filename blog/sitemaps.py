from datetime import datetime

from django.contrib.sitemaps import Sitemap

from posts.models import Post


class PostSitemap(Sitemap):
    """
    EN: Sitemap generator for published blog posts.
    FA: تولیدکننده نقشه سایت (Sitemap) برای پست‌های منتشر شده بلاگ.
    """

    changefreq = "weekly"
    priority = 0.9

    def items(self):
        """
        EN: Returns the list of published posts to include in the sitemap.
        FA: لیستی از پست‌های منتشر شده را برای درج در نقشه سایت بازمی‌گرداند.
        """
        return Post.objects.published()

    def lastmod(self, obj):
        """
        EN: Returns the last modification date (publication date) of a post.
        FA: تاریخ آخرین تغییر (تاریخ انتشار) یک پست را بازمی‌گرداند.
        """
        return obj.published_at

    def location(self, obj):
        """
        EN: Returns the URL location for a specific post.
        FA: آدرس URL را برای یک پست خاص بازمی‌گرداند.
        """
        return f"/posts/{obj.slug}"


class StaticViewSitemap(Sitemap):
    """
    EN: Sitemap generator for static pages and important application routes.
    FA: تولیدکننده نقشه سایت برای صفحات استاتیک و مسیرهای مهم اپلیکیشن.
    """

    priority = 0.5
    changefreq = "daily"

    def items(self):
        """
        EN: Returns the list of static URL paths.
        FA: لیستی از مسیرهای URL استاتیک را بازمی‌گرداند.
        """
        return [
            "/",
            "/about",
            "/register/login",
            "/register/signup",
            "/user-dashboard/",
        ]

    def lastmod(self, item):
        """
        EN: Returns the current time as the last modification for static views.
        FA: زمان فعلی را به عنوان آخرین تغییر برای نماهای استاتیک بازمی‌گرداند.
        """
        return datetime.now()

    def location(self, item):
        """
        EN: Returns the URL path for a static item.
        FA: مسیر URL را برای یک آیتم استاتیک بازمی‌گرداند.
        """
        return item
