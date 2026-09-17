import uuid
from django import forms
from django.db import models
from django.utils import timezone

from wagtail.models import Page
from wagtail.fields import StreamField
from wagtail.admin.panels import FieldPanel
from wagtail.admin.forms import WagtailAdminPageForm
from wagtail.admin.widgets import AdminDateTimeInput
from wagtail.images import get_image_model_string
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from .blocks import BlogStreamBlock
from wagtail_headless_preview.models import HeadlessPreviewMixin
from wagtail.api import APIField
from wagtail.fields import RichTextField
from typing import cast


from django.core.exceptions import ValidationError


class FutureAdminDateTimeInput(AdminDateTimeInput):
    """
    Custom DateTime picker widget that disables past dates in the Wagtail Admin UI picker.
    """
    def get_config(self):
        config = super().get_config()
        config["minDate"] = 0  # Disables past dates in the calendar picker
        return config


def generate_uuid_str():
    return str(uuid.uuid4())


def get_default_uncategorized_subcategory():
    category, _ = BlogCategory.objects.get_or_create(
        slug="uncategorized",
        defaults={
            "name": "Uncategorized",
            "description": "Default category for uncategorized posts",
        },
    )
    subcategory, _ = BlogSubCategory.objects.get_or_create(
        category=category,
        slug="uncategorized",
        defaults={"name": "Uncategorized"},
    )
    return subcategory


class BlogPageForm(WagtailAdminPageForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        parent = getattr(self, "parent_page", None)
        if parent and isinstance(parent.specific, BlogPage):
            if "subcategory" in self.fields:
                self.fields["subcategory"].widget = forms.HiddenInput()
                self.fields["subcategory"].required = False
            if "category" in self.fields:
                self.fields["category"].widget = forms.HiddenInput()
                self.fields["category"].required = False
        else:
            if "subcategory" in self.fields:
                self.fields["subcategory"].required = False
            if "category" in self.fields:
                self.fields["category"].required = False



# BlogPage DB Schema
class BlogPage(HeadlessPreviewMixin, Page):

    base_form_class = BlogPageForm

    short_description = models.TextField(
        max_length=500,
        blank=True,
    )

    category = models.ForeignKey(
        "blog.BlogCategory",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="blogs",
    )

    subcategory = models.ForeignKey(
        "blog.BlogSubCategory",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="blogs",
    )

    featured_image = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    body = StreamField(
        BlogStreamBlock(),
        blank=True,
        use_json_field=True,
    )


    published_date = models.DateTimeField(
        null=True,
        blank=True,
    )

    author = models.CharField(
        max_length=100,
        blank=True,
    )

    focus_keyphrase = models.CharField(
        max_length=100,
        blank=True,
        help_text="Primary keyword/phrase for search engines",
    )

    custom_meta_title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Custom SEO Meta Title (defaults to page title if blank)",
    )

    custom_meta_description = models.TextField(
        max_length=500,
        blank=True,
        help_text="Custom SEO Meta Description (defaults to short description if blank)",
    )

    keyphrase_synonyms = models.CharField(
        max_length=255,
        blank=True,
        help_text="Comma-separated synonyms or LSI keywords",
    )

    canonical_url = models.URLField(
        blank=True,
        help_text="Custom canonical URL if different from current post URL",
    )

    is_cornerstone = models.BooleanField(
        default=False,
        help_text="Mark if this is one of your most important, comprehensive articles",
    )

    robots_index = models.BooleanField(
        default=True,
        help_text="Allow search engines to index this article",
    )

    robots_follow = models.BooleanField(
        default=True,
        help_text="Allow search engines to follow links in this article",
    )

    social_title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Title for social media sharing (OG / Twitter)",
    )

    social_description = models.TextField(
        max_length=500,
        blank=True,
        help_text="Description for social media sharing",
    )

    social_image = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Custom image for social media sharing",
    )

    def get_author_name(self):
        if self.owner:
            full_name = self.owner.get_full_name()
            return full_name if full_name else self.owner.username
        return self.author if self.author else "Admin"

    def get_seo_report(self):
        from .seo_analyzer import BlogSEOAnalyzer
        analyzer = BlogSEOAnalyzer(self)
        return analyzer.run_seo_analysis()

    def get_readability_report(self):
        from .seo_analyzer import BlogSEOAnalyzer
        analyzer = BlogSEOAnalyzer(self)
        return analyzer.run_readability_analysis()

    def get_json_ld_schema(self):
        return {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": self.seo_title or self.title,
            "description": self.search_description or self.short_description,
            "author": {
                "@type": "Person",
                "name": self.get_author_name(),
            },
            "datePublished": self.published_date.isoformat() if self.published_date else None,
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": self.full_url or self.url or "",
            }
        }

    # Fields exposed to Wagtail API
    api_fields = [
        APIField("slug"),
        APIField("short_description"),
        APIField("category"),
        APIField("subcategory"),
        APIField("featured_image"),
        APIField("body"),
        APIField("published_date"),
        APIField("go_live_at"),
        APIField("expire_at"),
        APIField("author"),
        APIField("focus_keyphrase"),
        APIField("custom_meta_title"),
        APIField("custom_meta_description"),
        APIField("keyphrase_synonyms"),
        APIField("canonical_url"),
        APIField("is_cornerstone"),
        APIField("robots_index"),
        APIField("robots_follow"),
        APIField("social_title"),
        APIField("social_description"),
        APIField("social_image"),
        APIField("seo_report"),
        APIField("readability_report"),
        APIField("json_ld_schema"),
    ]

    def is_child_blog_page(self):
        parent = self.get_parent()
        return bool(parent and isinstance(cast(Page, parent).specific, BlogPage))

    def clean(self):
        super().clean()
        if self.is_child_blog_page():
            self.category = None
            self.subcategory = None
        else:
            if not self.subcategory:
                self.subcategory = get_default_uncategorized_subcategory()
            self.category = self.subcategory.category

        if self.published_date and self.published_date <= timezone.now():
            if not self.pk or not self.first_published_at:
                raise ValidationError(
                    {"published_date": "Publish date must be a future date and time."}
                )
            else:
                orig = BlogPage.objects.filter(pk=self.pk).values("published_date").first()
                if orig and orig["published_date"] != self.published_date:
                    raise ValidationError(
                        {"published_date": "Publish date must be a future date and time."}
                    )

    def save(self, *args, **kwargs):
        if self.is_child_blog_page():
            self.category = None
            self.subcategory = None
        else:
            if not self.subcategory:
                self.subcategory = get_default_uncategorized_subcategory()
            self.category = self.subcategory.category

        if self.published_date:
            self.go_live_at = self.published_date
        elif self.go_live_at:
            self.published_date = self.go_live_at

        super().save(*args, **kwargs)

    def save_revision(self, *args, **kwargs):
        if self.published_date and not kwargs.get("approved_go_live_at"):
            if self.published_date > timezone.now():
                kwargs["approved_go_live_at"] = self.published_date

        return super().save_revision(*args, **kwargs)

    content_panels = Page.content_panels + [  # type: ignore[bad-override]
        FieldPanel("short_description"),
        FieldPanel("featured_image"),
        FieldPanel("body"),
        FieldPanel("published_date", widget=FutureAdminDateTimeInput()),
        FieldPanel("subcategory"),
    ]



    promote_panels = Page.promote_panels + [  # type: ignore[bad-override]
        FieldPanel("focus_keyphrase"),
        FieldPanel("keyphrase_synonyms"),
        FieldPanel("canonical_url"),
        FieldPanel("is_cornerstone"),
        FieldPanel("robots_index"),
        FieldPanel("robots_follow"),
        FieldPanel("social_title"),
        FieldPanel("social_description"),
        FieldPanel("social_image"),
    ]


@register_snippet
class BlogCategory(models.Model):

    id = models.CharField(
        primary_key=True,
        max_length=36,
        default=generate_uuid_str,
        editable=False,
    )

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    slug = models.SlugField(
        max_length=100,
        unique=True,
    )

    description = models.TextField(
        blank=True,
        help_text="Category description",
    )

    focus_keyphrase = models.CharField(
        max_length=100,
        blank=True,
        help_text="Primary keyword/phrase for search engines",
    )

    seo_title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Custom SEO Meta Title (defaults to page title if blank)",
    )

    meta_description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Custom SEO Meta Description (defaults to page description if blank)",
    )

    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("description"),
        FieldPanel("focus_keyphrase"),
        FieldPanel("seo_title"),
        FieldPanel("meta_description")  
    ]

    def __str__(self):  # type: ignore[bad-override]
        return self.name


@register_snippet
class BlogSubCategory(models.Model):

    id = models.CharField(
        primary_key=True,
        max_length=36,
        default=generate_uuid_str,
        editable=False,
    )

    category = models.ForeignKey(
        BlogCategory,
        on_delete=models.CASCADE,
        related_name="subcategories",
    )

    name = models.CharField(
        max_length=100,
    )

    slug = models.SlugField(
        max_length=100,
        unique=True,
    )

    description = models.TextField(
        blank=True,
        help_text="Category description",
    )

    focus_keyphrase = models.CharField(
        max_length=100,
        blank=True,
        help_text="Primary keyword/phrase for search engines",
    )

    seo_title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Custom SEO Meta Title (defaults to page title if blank)",
    )

    meta_description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Custom SEO Meta Description (defaults to page description if blank)",
    )

    panels = [
        FieldPanel("category"),
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("description"),
        FieldPanel("focus_keyphrase"),
        FieldPanel("seo_title"),
        FieldPanel("meta_description")
    ]

    class Meta:
        verbose_name = "Blog Sub Category"
        verbose_name_plural = "Blog Sub Categories"

    def __str__(self):  # type: ignore[bad-override]
        return f"{self.category.name} -> {self.name}"


class BlogComment(models.Model):

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    id = models.CharField(
        primary_key=True,
        max_length=36,
        default=generate_uuid_str,
        editable=False,
    )

    blog = models.ForeignKey(
        BlogPage,
        on_delete=models.CASCADE,
        related_name="comments",
    )

    name = models.CharField(
        max_length=100,
    )

    email = models.EmailField()

    message = models.TextField()

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="replies",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    device_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    panels = [
        FieldPanel("blog"),
        FieldPanel("name"),
        FieldPanel("email"),
        FieldPanel("message"),
        FieldPanel("parent"),
        FieldPanel("device_id"),
        FieldPanel("status"),
    ]

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Blog Comment"
        verbose_name_plural = "Blog Comments"

    def __str__(self):
        return f"Comment by {self.name} on {self.blog.title} ({self.get_status_display()})"


class BlogCommentViewSet(SnippetViewSet):
    model = BlogComment
    menu_label = "Blog Comments"
    icon = "comment" # pyrefly: ignore[bad-override]
    list_display = ["name", "email", "blog", "device_id", "status", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["name", "email", "message", "device_id"]


register_snippet(BlogCommentViewSet)


@register_snippet
class BlogLike(models.Model):

    id = models.CharField(
        primary_key=True,
        max_length=36,
        default=generate_uuid_str,
        editable=False,
    )

    blog = models.ForeignKey(
        BlogPage,
        on_delete=models.CASCADE,
        related_name="likes",
    )

    device_id = models.CharField(
        max_length=255,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    panels = [
        FieldPanel("blog"),
        FieldPanel("device_id"),
    ]

    class Meta:
        unique_together = ("blog", "device_id")
        verbose_name = "Blog Like"
        verbose_name_plural = "Blog Likes"

    def __str__(self):
        return f"Like by {self.device_id} on {self.blog.title}"


 