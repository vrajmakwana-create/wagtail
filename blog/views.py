from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .responses import success_response

from .models import BlogPage, BlogCategory
from .serializers import (
    BlogListSerializer,
    BlogDetailSerializer,
    CategorySerializer,
)

from rest_framework.views import APIView

from django.contrib.contenttypes.models import ContentType
from wagtail_headless_preview.models import PagePreview


from core.responses import APIResponse
from core.pagination import StandardResultsSetPagination

from .models import BlogPage
from .serializers import BlogListSerializer


class BlogListAPIView(APIView):

    def get(self, request):

        blogs = (
            BlogPage.objects
            .live()
            .specific()
            .order_by("-published_date")
        )

        # Get category from query params
        category = request.query_params.get("category")

        # Filter by category slug
        if category:
            blogs = blogs.filter(
                category__slug=category
            )

        # Pagination
        paginator = StandardResultsSetPagination()

        page = paginator.paginate_queryset(
            blogs,
            request,
            view=self,
        )

        serializer = BlogListSerializer(
            page,
            many=True,
            context={"request": request},
        )

        return paginator.get_paginated_response(
            serializer.data
        )

class BlogDetailAPIView(APIView):

    def get(self, request, slug):

        try:
            blog = (
                BlogPage.objects
                .live()
                .specific()
                .get(slug=slug)
            )

        except BlogPage.DoesNotExist:  # type: ignore[bad-override]

            return Response(
                {
                    "detail": "Blog not found"
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = BlogDetailSerializer(blog, context={"request": request})

        return success_response(
            message="Blog Detail fetched successfully",
            result=serializer.data
        )


class CategoryListAPIView(APIView):

    def get(self, request):

        categories = BlogCategory.objects.all()  # type: ignore[bad-override]

        serializer = CategorySerializer(
            categories,
            many=True
        )

        return success_response(
            message="Categories fetched successfully",
            result=serializer.data
        )


class BlogPreviewAPIView(APIView):

    def get(self, request):
        token = request.query_params.get("token")
        content_type_str = request.query_params.get("content_type", "blog.blogpage")

        if not token:
            return Response(
                {"detail": "Preview token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            app_label, model = content_type_str.split(".")
            content_type = ContentType.objects.get(
                app_label=app_label,
                model=model,
            )
            page_preview = PagePreview.objects.get(  # type: ignore[bad-override]
                content_type=content_type, 
                token=token,
            )
        except (ValueError, ContentType.DoesNotExist, PagePreview.DoesNotExist):  # type: ignore[bad-override]
            return Response(
                {"detail": "Invalid content_type or preview token."},
                status=status.HTTP_404_NOT_FOUND,
            )

        page = page_preview.as_page()
        serializer = BlogDetailSerializer(page, context={"request": request})

        return success_response(
            message="Preview data fetched successfully",
            result=serializer.data,
        )
