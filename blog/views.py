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

        except BlogPage.DoesNotExist:

            return Response(
                {
                    "detail": "Blog not found"
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = BlogDetailSerializer(blog)

        return success_response(
            message="Blog Detail fetched successfully",
            result=serializer.data
        )

class CategoryListAPIView(APIView):

    def get(self, request):

        categories = BlogCategory.objects.all()

        serializer = CategorySerializer(
            categories,
            many=True
        )

        return success_response(
            message="Categories fetched successfully",
            result=serializer.data
        )