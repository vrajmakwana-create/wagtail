from django.shortcuts import render
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .responses import success_response, error_response

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from wagtail_headless_preview.models import PagePreview

from .models import BlogPage, BlogCategory, BlogSubCategory, BlogComment, BlogLike
from .serializers import (
    BlogListSerializer,
    BlogDetailSerializer,
    CategorySerializer,
    SubCategorySerializer,
    BlogCommentCreateSerializer,
    BlogCommentSerializer,
    get_user_author_details,
)

from core.responses import APIResponse
from core.pagination import StandardResultsSetPagination


class BlogListAPIView(APIView):

    def get(self, request):

        blogs = (
            BlogPage.objects
            .live()
            .specific()
            .select_related("category", "subcategory")
            .filter(subcategory__isnull=False)
            .order_by("-published_date")
        )

        # Get category & subcategory & search from query params
        category = request.query_params.get("category")
        subcategory = request.query_params.get("subcategory")
        search_query = request.query_params.get("search") or request.query_params.get("q")
        author = request.query_params.get("author")
        current_blog_slug = request.query_params.get("current_blog_slug")

        # Return empty result if category or subcategory is 'uncategorized'
        if (category and str(category).strip().lower() == "uncategorized") or (
            subcategory and str(subcategory).strip().lower() == "uncategorized"
        ):
            blogs = BlogPage.objects.none()

        # Filter by category (slug or id)
        if category:
            category_query = Q(
                Q(category__slug=category),
                Q(category__id=category),
                Q(subcategory__category__slug=category),
                Q(subcategory__category__id=category),
                _connector=Q.OR,
            )
            
            blogs = blogs.filter(
                category_query,
            ).distinct()    

        # Filter by subcategory (slug or id)
        if subcategory:
            blogs = blogs.filter(
                Q(subcategory__slug=subcategory) | Q(subcategory__id=subcategory)
            )

        # Filter by search query
        if search_query:
            blogs = blogs.filter(
                Q(title__icontains=search_query) |
                Q(short_description__icontains=search_query) |
                Q(author__icontains=search_query) |
                Q(owner__first_name__icontains=search_query) |
                Q(owner__last_name__icontains=search_query) |
                Q(owner__username__icontains=search_query) |
                Q(focus_keyphrase__icontains=search_query) 
            ).distinct()

        # Filter by author (username, name, author field, or user id)
        if author:
            author_filter = (
                Q(owner__first_name__icontains=author) |
                Q(owner__last_name__icontains=author) |
                Q(owner__username__icontains=author) |
                Q(author__icontains=author)
            )
            if author.isdigit():
                author_filter |= Q(owner__id=int(author))
            blogs = blogs.filter(author_filter).distinct()
        
        # Filter by current blog (slug or id)
        if current_blog_slug:
            blogs = blogs.exclude(Q(slug=current_blog_slug))


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
                .select_related("category", "subcategory")
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

        categories = (
            BlogCategory.objects
            .prefetch_related("subcategories")
            .exclude(slug="uncategorized")
            .all()
        )  # type: ignore[bad-override]

        serializer = CategorySerializer(
            categories,
            many=True
        )

        return success_response(
            message="Categories fetched successfully",
            result=serializer.data
        )


class SubCategoryListAPIView(APIView):

    def get(self, request):

        subcategories = (
            BlogSubCategory.objects
            .select_related("category")
            .exclude(slug="uncategorized")
            .all()
        )  # type: ignore[bad-override]

        category = request.query_params.get("category")
        if category:
            subcategories = subcategories.filter(
                Q(category__slug=category) | Q(category__id=category)
            )

        serializer = SubCategorySerializer(
            subcategories,
            many=True
        )

        return success_response(
            message="Subcategories fetched successfully",
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
        if not getattr(page, "pk", None):
            page.pk = 0
        serializer = BlogDetailSerializer(page, context={"request": request})

        return success_response(
            message="Preview data fetched successfully",
            result=serializer.data,
        )


class BlogCommentListCreateAPIView(APIView):

    def get(self, request, slug):
        try:
            blog = BlogPage.objects.live().get(slug=slug)
        except BlogPage.DoesNotExist:
            return Response(
                {"detail": "Blog not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        device_id = request.query_params.get("device_id")
        if device_id:
            status_filter = Q(status=BlogComment.STATUS_APPROVED) | Q(
                status=BlogComment.STATUS_PENDING, device_id=device_id
            )
        else:
            status_filter = Q(status=BlogComment.STATUS_APPROVED)

        top_level_comments = (
            BlogComment.objects
            .filter(
                Q(blog=blog, parent__isnull=True) & status_filter
            )
            .order_by("-created_at")
        )

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(
            top_level_comments,
            request,
            view=self,
        )

        serializer = BlogCommentSerializer(
            page,
            many=True,
            context={"request": request},
        )

        return paginator.get_paginated_response(serializer.data)

    def post(self, request, slug):
        try:
            blog = BlogPage.objects.live().get(slug=slug)
        except BlogPage.DoesNotExist:
            return Response(
                {"detail": "Blog not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = BlogCommentCreateSerializer(
            data=request.data,
            context={"request": request, "blog": blog},
        )

        if serializer.is_valid():
            comment = serializer.save(blog=blog, status=BlogComment.STATUS_PENDING)
            response_serializer = BlogCommentSerializer(comment, context={"request": request})
            return success_response(
                message="Comment submitted successfully and is awaiting admin approval.",
                result=response_serializer.data,
                status_code=status.HTTP_201_CREATED,
            )

        return error_response(
            message="Invalid comment data",
            result=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class BlogLikeToggleAPIView(APIView):

    def post(self, request, slug):
        device_id = request.data.get("device_id")
        if not device_id:
            return error_response(
                message="device_id is required",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            blog = BlogPage.objects.live().get(slug=slug)
        except BlogPage.DoesNotExist:
            return Response(
                {"detail": "Blog not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        like_obj, created = BlogLike.objects.get_or_create(
            blog=blog,
            device_id=device_id,
        )

        if not created:
            like_obj.delete()
            is_liked = False
            msg = "Blog unliked successfully"
        else:
            is_liked = True
            msg = "Blog liked successfully"

        total_likes = blog.likes.count()

        return success_response(
            message=msg,
            result={
                "is_liked": is_liked,
                "total_likes": total_likes,
            },
        )


class AuthorBlogListAPIView(APIView):

    def get(self, request, user_id):
        User = get_user_model()
        user = User.objects.filter(id=user_id).first()

        if not user:
            return Response(
                {"detail": "Author not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        blogs = (
            BlogPage.objects
            .live()
            .specific()
            .select_related("category", "subcategory")
            .filter(owner_id=user_id)
            .order_by("-published_date")
        )

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

        response = paginator.get_paginated_response(
            serializer.data
        )

        author_data = get_user_author_details(user, context={"request": request})

        response.data = {
            "author": author_data,
            **response.data,
        }

        return response




