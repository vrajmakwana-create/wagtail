from django.urls import include, path

from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls

from .api import api_router


urlpatterns = [
    # Wagtail Admin
    path("admin/", include(wagtailadmin_urls)),

    # Your existing Blog API
    path("api/", include("blog.urls")),

    # Wagtail API + Headless Preview API
    path("api/v2/", api_router.urls),

    # Wagtail Pages - MUST stay last
    path("", include(wagtail_urls)),
]