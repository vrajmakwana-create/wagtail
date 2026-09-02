from rest_framework import serializers

from .models import BlogPage, BlogCategory
from wagtail.rich_text import RichText
from wagtail.images import get_image_model

WagtailImage = get_image_model()


class CategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = BlogCategory

        fields = [
            "id",
            "name",
            "slug",
        ]


class ImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = WagtailImage
        fields = [
            "id",
            "title",
            "url",
            "width",
            "height",
        ]

    def get_url(self, obj):
        if not obj or not getattr(obj, "file", None):
            return None
        url = obj.file.url
        request = self.context.get("request") if getattr(self, "context", None) else None
        if request and url.startswith("/"):
            return request.build_absolute_uri(url)
        return url


class StreamFieldSerializer(serializers.Field):

    def to_representation(self, value):
        return self.convert_value(value)

    def convert_value(self, value):

        # Wagtail Image instance
        if isinstance(value, WagtailImage):
            request = getattr(self, "context", {}).get("request") if getattr(self, "context", None) else None
            url = value.file.url if getattr(value, "file", None) else ""
            if request and url.startswith("/"):
                url = request.build_absolute_uri(url)
            return {
                "id": value.id,
                "title": value.title,
                "url": url,
                "width": value.width,
                "height": value.height,
            }

        # RichText -> HTML string
        if isinstance(value, RichText):
            return str(value)

        # StreamValue / StreamChild
        if hasattr(value, "block_type") and hasattr(value, "value"):
            return {
                "type": value.block_type,
                "id": str(value.id) if getattr(value, "id", None) else None,
                "value": self.convert_value(value.value),
            }

        # Dictionary / StructBlock
        if isinstance(value, dict):
            return {
                key: self.convert_value(val)
                for key, val in value.items()
            }

        # List / ListBlock
        if isinstance(value, (list, tuple)):
            return [
                self.convert_value(item)
                for item in value
            ]

        # Handle StreamValue
        if hasattr(value, "__iter__") and not isinstance(
            value, (str, bytes)
        ):
            try:
                return [
                    self.convert_value(item)
                    for item in value
                ]
            except TypeError:
                pass

        return value


class BlogListSerializer(serializers.ModelSerializer):

    category = CategorySerializer(read_only=True)
    featured_image = ImageSerializer(read_only=True)

    class Meta:
        model = BlogPage

        fields = [
            "id",
            "title",
            "slug",
            "short_description",
            "category",
            "featured_image",
            "author",
            "published_date",
        ]


class BlogChildSerializer(serializers.ModelSerializer):

    class Meta:
        model = BlogPage

        fields = [
            "id",
            "title",
            "slug",
            "short_description",
        ]


class BlogDetailSerializer(serializers.ModelSerializer):

    category = CategorySerializer(read_only=True)
    featured_image = ImageSerializer(read_only=True)

    body = StreamFieldSerializer()

    children = serializers.SerializerMethodField()

    class Meta:
        model = BlogPage

        fields = [
            "id",
            "title",
            "slug",
            "short_description",
            "category",
            "featured_image",
            "author",
            "published_date",
            "body",
            "children",
        ]

    def get_children(self, obj):

        children = (
            obj
            .get_children()
            .live()
            .specific()
        )

        return BlogChildSerializer(
            children,
            many=True
        ).data