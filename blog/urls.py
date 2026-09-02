from django.urls import path

from .views import (
    BlogListAPIView,
    BlogDetailAPIView,
    BlogPreviewAPIView,
    CategoryListAPIView,
)


urlpatterns = [

    path(
        "blogs/",
        BlogListAPIView.as_view(),
        name="blog-list",
    ),

    path(
        "blogs/preview/",
        BlogPreviewAPIView.as_view(),
        name="blog-preview",
    ),

    path(
        "blogs/categories/",
        CategoryListAPIView.as_view(),
        name="category-list",
    ),

    path(
        "blogs/<slug:slug>/",
        BlogDetailAPIView.as_view(),
        name="blog-detail",
    ),
]