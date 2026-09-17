from rest_framework import serializers

from .models import BlogPage, BlogCategory, BlogSubCategory, BlogComment, BlogLike
from wagtail.rich_text import RichText
from wagtail.images import get_image_model
from wagtail.embeds.blocks import EmbedValue


WagtailImage = get_image_model()


class SubCategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = BlogSubCategory

        fields = [
            "id",
            "name",
            "slug",
            "description",
            "focus_keyphrase",
            "seo_title",
            "meta_description"
        ]


class CategorySimpleSerializer(serializers.ModelSerializer):

    description = serializers.SerializerMethodField()

    class Meta:
        model = BlogCategory

        fields = [
            "id",
            "name",
            "slug",
            "description",
        ]

    def get_description(self, obj):
        return str(obj.description) if obj.description else ""

class CategoryBlogDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = BlogCategory

        fields = [
            "id",
            "name",
            "slug",
        ]


class CategorySerializer(serializers.ModelSerializer):

    subcategories = SubCategorySerializer(many=True, read_only=True)
    description = serializers.SerializerMethodField()

    class Meta:
        model = BlogCategory

        fields = [
            "id",
            "name",
            "slug",
            "description",
            "focus_keyphrase",
            "seo_title",
            "meta_description", 
            "subcategories",
        ]

    def get_description(self, obj):
        return str(obj.description) if obj.description else ""


class ImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    alt_text = serializers.SerializerMethodField()

    class Meta:
        model = WagtailImage
        fields = [
            "id",
            "title",
            "alt_text",
            "url",
            "width",
            "height",
        ]

    def get_alt_text(self, obj):
        if not obj:
            return ""
        return getattr(obj, "alt_text", None) or getattr(obj, "title", "")

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

        # Wagtail EmbedValue -> dict with url and iframe html
        if isinstance(value, EmbedValue):
            return {
                "url": value.url,
                "html": str(value.html) if getattr(value, "html", None) else "",
            }

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

class BlogChildSerializer(serializers.ModelSerializer):

    class Meta:
        model = BlogPage

        fields = [
            "id",
            "title",
            "slug",
        ]

def get_user_author_details(user, context=None):
    if not user:
        return None

    name = user.get_full_name() or user.username
    bio = ""
    profile_image_url = None

    profile = getattr(user, "profile", None)
    if profile:
        bio = profile.bio or ""
        profile_image_url = profile.profile_image_url
        if not profile_image_url and profile.profile_image:
            request = context.get("request") if context else None
            url = profile.profile_image.url
            if request and url.startswith("/"):
                profile_image_url = request.build_absolute_uri(url)
            else:
                profile_image_url = url

    return {
        "id": user.id,
        "name": name,
        "bio": bio,
        "profile_image_url": profile_image_url,
    }


def get_author_details(obj, context=None):
    if obj.owner:
        return get_user_author_details(obj.owner, context)

    return {
        "id": None,
        "name": obj.author if obj.author else "Admin",
        "bio": "",
        "profile_image_url": None,
    }



class BlogCommentCreateSerializer(serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(
        queryset=BlogComment.objects.all(),
        required=False,
        allow_null=True,
    )
    device_id = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=255,
    )

    class Meta:
        model = BlogComment
        fields = [
            "name",
            "email",
            "message",
            "parent",
            "device_id",
        ]

    def validate_parent(self, value):
        if value:
            blog = self.context.get("blog")
            if blog and value.blog != blog:
                raise serializers.ValidationError(
                    "Parent comment must belong to the same blog."
                )
        return value


class BlogCommentSerializer(serializers.ModelSerializer):
    replies = serializers.SerializerMethodField()

    class Meta:
        model = BlogComment
        fields = [
            "id",
            "name",
            "email",
            "message",
            "parent",
            "device_id",
            "status",
            "created_at",
            "replies",
        ]

    def get_replies(self, obj):
        from django.db.models import Q
        request = self.context.get("request") if self.context else None
        device_id = request.query_params.get("device_id") if request else None

        if device_id:
            reply_filter = Q(status=BlogComment.STATUS_APPROVED) | Q(
                status=BlogComment.STATUS_PENDING, device_id=device_id
            )
        else:
            reply_filter = Q(status=BlogComment.STATUS_APPROVED)

        replies = obj.replies.filter(reply_filter).order_by("created_at")
        return BlogCommentSerializer(replies, many=True, context=self.context).data


class BlogListSerializer(serializers.ModelSerializer):

    category = CategorySimpleSerializer(read_only=True)
    subcategory = SubCategorySerializer(read_only=True)
    featured_image = ImageSerializer(read_only=True)
    social_image = ImageSerializer(read_only=True)
    children = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()
    body = StreamFieldSerializer()

    seo_title = serializers.SerializerMethodField()
    seo_description = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = BlogPage

        fields = [
            "id",
            "title",
            "slug",
            "short_description",
            "category",
            "subcategory",
            "body",
            "children",
            "featured_image",
            "author",
            "published_date",
            "likes_count",
            "comments_count",
            "seo_title",
            "seo_description",
            "social_title",
            "social_description",
            "social_image",
        ]

    def get_author(self, obj):
        return get_author_details(obj, self.context)

    def get_seo_title(self, obj):
        return obj.seo_title if obj.seo_title else obj.title

    def get_seo_description(self, obj):
        return obj.search_description if obj.search_description else obj.short_description

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_comments_count(self, obj):
        return obj.comments.filter(status=BlogComment.STATUS_APPROVED).count()

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


class BlogDetailSerializer(serializers.ModelSerializer):

    category = CategoryBlogDetailSerializer(read_only=True)
    subcategory = SubCategorySerializer(read_only=True)
    featured_image = ImageSerializer(read_only=True)
    author = serializers.SerializerMethodField()

    body = StreamFieldSerializer()
    children = serializers.SerializerMethodField()
    metadata = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = BlogPage

        fields = [
            "id",
            "title",
            "slug",
            "short_description",
            "category",
            "subcategory",
            "featured_image",
            "author",
            "published_date",
            "likes_count",
            "comments_count",
            "is_liked",
            "body",
            "children",
            "metadata",
        ]

    def get_author(self, obj):
        return get_author_details(obj, self.context)

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_comments_count(self, obj):
        return obj.comments.filter(status=BlogComment.STATUS_APPROVED).count()

    def get_is_liked(self, obj):
        request = self.context.get("request")
        if request:
            device_id = request.query_params.get("device_id")
            if device_id:
                return obj.likes.filter(device_id=device_id).exists()
        return False

    def get_metadata(self, obj):
        request = self.context.get("request")
        social_image_data = ImageSerializer(obj.social_image, context={"request": request}).data if obj.social_image else None

        return {
            "focus_keyphrase": obj.focus_keyphrase,
            "keyphrase_synonyms": obj.keyphrase_synonyms,
            "canonical_url": obj.canonical_url,
            "is_cornerstone": obj.is_cornerstone,
            "robots_index": obj.robots_index,
            "robots_follow": obj.robots_follow,
            "seo_title": obj.seo_title if obj.seo_title else obj.title,
            "seo_description": obj.search_description if obj.search_description else obj.short_description,
            "social_title": obj.social_title,
            "social_description": obj.social_description,
            "social_image": social_image_data,
            "seo_report": obj.get_seo_report(),
            "readability_report": obj.get_readability_report(),
            "json_ld_schema": obj.get_json_ld_schema(),
        }

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


