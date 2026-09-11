from django.urls import path

from .views import (
    BlogListAPIView,
    BlogDetailAPIView,
    BlogPreviewAPIView,
    CategoryListAPIView,
    SubCategoryListAPIView,
    BlogCommentListCreateAPIView,
    BlogLikeToggleAPIView,
    AuthorBlogListAPIView,
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
        "blogs/subcategories/",
        SubCategoryListAPIView.as_view(),
        name="subcategory-list",
    ),

    path(
        "blogs/author/<int:user_id>/",
        AuthorBlogListAPIView.as_view(),
        name="author-blog-list",
    ),


    path(
        "blogs/<slug:slug>/comments/",
        BlogCommentListCreateAPIView.as_view(),
        name="blog-comments",
    ),

    path(
        "blogs/<slug:slug>/like/",
        BlogLikeToggleAPIView.as_view(),
        name="blog-like-toggle",
    ),

    path(
        "blogs/<slug:slug>/",
        BlogDetailAPIView.as_view(),
        name="blog-detail",
    ),
]


