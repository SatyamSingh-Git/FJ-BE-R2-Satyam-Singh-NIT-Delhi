from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'preferred_currency', 'email_notifications', 'created_at']
    list_filter = ['preferred_currency', 'email_notifications']
    search_fields = ['user__email', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
