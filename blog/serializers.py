from rest_framework import serializers

from .models import BlogPage, BlogCategory
from wagtail.rich_text import RichText


class CategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = BlogCategory

        fields = [
            "id",
            "name",
            "slug",
        ]

class StreamFieldSerializer(serializers.Field):

    def to_representation(self, value):
        return self.convert_value(value)

    def convert_value(self, value):

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
# class StreamFieldSerializer(serializers.Field):

#     def to_representation(self, value):

#         result = []

#         for block in value:

#             block_value = block.value

#             if block.block_type == "image":

#                 image = block_value

#                 block_value = {
#                     "id": image.id,
#                     "title": image.title,
#                     "url": image.file.url,
#                     "width": image.width,
#                     "height": image.height,
#                 }

#             result.append({
#                 "type": block.block_type,
#                 "value": block_value,
#             })

#         return result

#     def serialize_value(self, value):
#         if isinstance(value, RichText):
#             return str(value)

#         if isinstance(value, list):
#             return [
#                 self.serialize_value(item)
#                 for item in value
#             ]

#         if isinstance(value, dict):
#             return {
#                 key: self.serialize_value(val)
#                 for key, val in value.items()
#             }

#         return value


class BlogListSerializer(serializers.ModelSerializer):

    category = CategorySerializer(read_only=True)

    class Meta:
        model = BlogPage

        fields = [
            "id",
            "title",
            "slug",
            "short_description",
            "category",
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