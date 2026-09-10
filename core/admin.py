from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "bio", "profile_image_url"]
    search_fields = ["user__username", "user__first_name", "user__last_name", "bio"]

