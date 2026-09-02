from django.db import models

# Create your models here.
from django.db import models

from wagtail.models import Page
from wagtail.fields import StreamField
from wagtail.admin.panels import FieldPanel
from wagtail.images import get_image_model_string
from wagtail.snippets.models import register_snippet
from .blocks import BlogStreamBlock


# BlogPage DB Schema
class BlogPage(Page):

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

    content_panels = Page.content_panels + [
        FieldPanel("short_description"),
        FieldPanel("featured_image"),
        FieldPanel("body"),
        FieldPanel("published_date"),
        FieldPanel("author"),
        FieldPanel("category"),
    ]


@register_snippet
class BlogCategory(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    slug = models.SlugField(
        max_length=100,
        unique=True,
    )

    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
    ]

    def __str__(self):
        return self.name