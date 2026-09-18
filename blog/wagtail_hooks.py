import json
from django.urls import path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from wagtail import hooks
from blog.seo_analyzer import BlogSEOAnalyzer


class MockBlogPage:
    def __init__(self, data: dict):
        self.title = data.get("title", "")
        self.slug = data.get("slug", "")
        self.focus_keyphrase = data.get("focus_keyphrase", "")
        self.keyphrase_synonyms = data.get("keyphrase_synonyms", "")
        self.seo_title = data.get("seo_title") or data.get("custom_meta_title") or self.title
        self.custom_meta_title = data.get("custom_meta_title", "")
        self.search_description = data.get("search_description") or data.get("custom_meta_description") or data.get("short_description") or ""
        self.custom_meta_description = data.get("custom_meta_description", "")
        self.short_description = data.get("short_description", "")
        self.canonical_url = data.get("canonical_url", "")
        self.body_html = data.get("body_html", "")
        self.body = data.get("body_html", "")
        self.featured_image_alt = data.get("featured_image_alt", "")
        
        feat_img_val = data.get("featured_image")
        if feat_img_val:
            class MockImage:
                title = data.get("featured_image_alt", "") or "Featured Image"
            self.featured_image = MockImage()
        else:
            self.featured_image = None


@csrf_exempt
def seo_analysis_preview_view(request):
    """
    AJAX endpoint for Wagtail admin to run real-time SEO & Readability analysis
    on draft form content as the author writes.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)

    try:
        if request.content_type == "application/json":
            payload = json.loads(request.body.decode("utf-8"))
        else:
            payload = request.POST.dict()

        mock_page = MockBlogPage(payload)
        analyzer = BlogSEOAnalyzer(mock_page)

        seo_report = analyzer.run_seo_analysis()
        readability_report = analyzer.run_readability_analysis()

        return JsonResponse({
            "success": True,
            "seo_report": seo_report,
            "readability_report": readability_report,
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@hooks.register("register_admin_urls")
def register_seo_analysis_admin_urls():
    return [
        path("blog/seo-analysis-preview/", seo_analysis_preview_view, name="blog_seo_analysis_preview"),
    ]
