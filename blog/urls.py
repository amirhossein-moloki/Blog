from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.contrib.sitemaps.views import sitemap
from .sitemaps import (
    PostSitemap,
    StaticViewSitemap,
)

# Import drf-spectacular views
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .ckeditor_views import ckeditor5_upload
from posts.ckeditor_views import ckeditor_upload_view
from .views import page_not_found_view

handler404 = page_not_found_view

sitemaps = {
    "posts": PostSitemap,
    "static": StaticViewSitemap,
}

urlpatterns = [
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
    path("api/users/", include("users.urls")),
    path("api/posts/", include("posts.urls", namespace="posts")),
    path("api/medias/", include("medias.urls", namespace="medias")),
    path("api/interactions/", include("interactions.urls", namespace="interactions")),
    path("api/pages/", include("pages.urls", namespace="pages")),
    path("api/navigation/", include("navigation.urls", namespace="navigation")),
    path("api/editor/upload/", ckeditor_upload_view, name="ckeditor_upload"),
]

# --- Debug Tools & Static/Media ---
if settings.DEBUG:
    urlpatterns += [path("api/silk/", include("silk.urls", namespace="silk"))]
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
