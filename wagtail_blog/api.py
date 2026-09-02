from django.contrib.contenttypes.models import ContentType

from rest_framework.response import Response

from wagtail.api.v2.router import WagtailAPIRouter
from wagtail.api.v2.views import PagesAPIViewSet

from wagtail_headless_preview.models import PagePreview


# Create API router
api_router = WagtailAPIRouter("wagtailapi")


class PagePreviewAPIViewSet(PagesAPIViewSet):
    known_query_parameters = PagesAPIViewSet.known_query_parameters.union(
        ["content_type", "token"]
    )

    def listing_view(self, request):
        # Use detail serialization format
        self.action = "detail_view"
        return self.detail_view(request, 0)

    def detail_view(self, request, pk):
        page = self.get_object()
        serializer = self.get_serializer(page)
        return Response(serializer.data)

    def get_object(self):
        # Get content_type, for example: blog.blogpage
        app_label, model = self.request.GET["content_type"].split(".")

        content_type = ContentType.objects.get(
            app_label=app_label,
            model=model,
        )

        # Get preview using the token
        page_preview = PagePreview.objects.get(  # type: ignore[bad-override]
            content_type=content_type,
            token=self.request.GET["token"],
        )

        # Convert preview into the draft page
        page = page_preview.as_page()

        # Fake ID for Wagtail API serialization if page has no ID
        if not page.pk:
            page.pk = 0

        return page


# Register endpoint
api_router.register_endpoint(
    "page_preview",
    PagePreviewAPIViewSet,
)