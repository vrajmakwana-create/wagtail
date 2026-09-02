from django.db import models

from wagtail.models import Page
from wagtail_headless_preview.models import HeadlessPreviewMixin


class HomePage(HeadlessPreviewMixin, Page):
    pass

