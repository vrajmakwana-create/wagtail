# Data migration to create default Uncategorized category and subcategory

from django.db import migrations


def create_uncategorized_defaults(apps, schema_editor):
    BlogCategory = apps.get_model("blog", "BlogCategory")
    BlogSubCategory = apps.get_model("blog", "BlogSubCategory")

    category, _ = BlogCategory.objects.get_or_create(
        slug="uncategorized",
        defaults={
            "name": "Uncategorized",
            "description": "Default category for uncategorized posts",
        },
    )
    BlogSubCategory.objects.get_or_create(
        category=category,
        slug="uncategorized",
        defaults={"name": "Uncategorized"},
    )


def reverse_uncategorized_defaults(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0014_blogcomment_device_id"),
    ]

    operations = [
        migrations.RunPython(create_uncategorized_defaults, reverse_uncategorized_defaults),
    ]
