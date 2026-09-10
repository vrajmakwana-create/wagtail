import os
import boto3
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from wagtail.snippets.models import register_snippet
from wagtail.admin.panels import FieldPanel


@register_snippet
class UserProfile(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    bio = models.TextField(
        blank=True,
        default="",
        help_text="Author biography",
    )

    profile_image = models.ImageField(
        upload_to="profile_images/",
        blank=True,
        null=True,
        help_text="Profile image of the user",
    )

    profile_image_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="S3 URL or public URL of the profile image",
    )

    panels = [
        FieldPanel("user"),
        FieldPanel("bio"),
        FieldPanel("profile_image"),
    ]

    def __str__(self):
        full_name = self.user.get_full_name()
        return full_name if full_name else self.user.username

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.profile_image:
            use_s3 = getattr(settings, "USE_S3", False)
            bucket_name = getattr(settings, "AWS_STORAGE_BUCKET_NAME", os.getenv("AWS_STORAGE_BUCKET_NAME"))
            access_key = getattr(settings, "AWS_ACCESS_KEY_ID", os.getenv("AWS_ACCESS_KEY_ID"))
            secret_key = getattr(settings, "AWS_SECRET_ACCESS_KEY", os.getenv("AWS_SECRET_ACCESS_KEY"))
            region_name = getattr(settings, "AWS_S3_REGION_NAME", os.getenv("AWS_S3_REGION_NAME", "us-east-1"))

            if use_s3 or (bucket_name and access_key and secret_key):
                try:
                    s3_client = boto3.client(
                        "s3",
                        aws_access_key_id=access_key,
                        aws_secret_access_key=secret_key,
                        region_name=region_name,
                    )
                    file_obj = self.profile_image.file
                    file_obj.seek(0)
                    file_name = os.path.basename(self.profile_image.name)
                    s3_key = f"media/profile_images/{file_name}"

                    content_type = getattr(file_obj, "content_type", "image/jpeg")
                    s3_client.upload_fileobj(
                        file_obj,
                        bucket_name,
                        s3_key,
                        ExtraArgs={"ContentType": content_type},
                    )

                    s3_url = f"https://{bucket_name}.s3.{region_name}.amazonaws.com/{s3_key}"
                    if self.profile_image_url != s3_url:
                        self.profile_image_url = s3_url
                        super().save(update_fields=["profile_image_url"])
                except Exception as e:
                    print(f"S3 Upload notice: {e}")
                    if self.profile_image and hasattr(self.profile_image, "url"):
                        url = self.profile_image.url
                        if self.profile_image_url != url:
                            self.profile_image_url = url
                            super().save(update_fields=["profile_image_url"])
            else:
                if self.profile_image and hasattr(self.profile_image, "url"):
                    url = self.profile_image.url
                    if self.profile_image_url != url:
                        self.profile_image_url = url
                        super().save(update_fields=["profile_image_url"])



@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

