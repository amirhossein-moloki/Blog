from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

# EN: Import drf-spectacular views for API documentation.
# FA: وارد کردن نماهای drf-spectacular برای مستندات API.
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from posts.ckeditor_views import ckeditor_upload_view

from .ckeditor_views import ckeditor5_upload
from .sitemaps import (
    PostSitemap,
    StaticViewSitemap,
)
from .views import page_not_found_view

# EN: Custom 404 handler for the project.
# FA: مدیریت‌کننده سفارشی خطای ۴۰۴ برای پروژه.
handler404 = page_not_found_view

sitemaps = {
    "posts": PostSitemap,
    "static": StaticViewSitemap,
}

urlpatterns = [
    # EN: Sitemap XML endpoint.
    # FA: اندپوینت XML نقشه سایت.
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    # --- JWT Token Authentication ---
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # --- Admin Panel ---
    path(
        "ckeditor5/image_upload/",
        ckeditor5_upload,
        name="ck_editor_5_upload_file",
    ),
    path("ckeditor5/", include("django_ckeditor_5.urls")),
    path("admin/", admin.site.urls),
    # --- Third-party integrations ---
    path("api/select2/", include("django_select2.urls")),
    # --- API Documentation (drf-spectacular) ---
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    # --- App URLs ---
    path("api/", include("users.urls")),
    path("api/", include("posts.urls", namespace="posts")),
    path("api/", include("medias.urls", namespace="medias")),
    path("api/", include("interactions.urls", namespace="interactions")),
    path("api/", include("pages.urls", namespace="pages")),
    path("api/", include("navigation.urls", namespace="navigation")),
    path("api/editor/upload/", ckeditor_upload_view, name="ckeditor_upload"),
]

# --- Debug Tools & Static/Media ---
if settings.DEBUG:
    # EN: Include Silk profiling tool and serve media files directly in development.
    # FA: شامل کردن ابزار پروفایلینگ Silk و ارائه مستقیم فایل‌های رسانه در محیط توسعه.
    urlpatterns += [path("api/silk/", include("silk.urls", namespace="silk"))]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
