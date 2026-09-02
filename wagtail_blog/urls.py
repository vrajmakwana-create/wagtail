from django.urls import include, path
from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls

urlpatterns = [
    # Wagtail admin
    path("admin/", include(wagtailadmin_urls)),

    # API
    path(
        "api/",
        include("blog.urls")
    ),

    # Wagtail pages
    path("", include(wagtail_urls)),
]