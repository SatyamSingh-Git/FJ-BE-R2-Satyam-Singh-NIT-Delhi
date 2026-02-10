from django.contrib import admin
from .models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'type', 'icon', 'color', 'is_active', 'transaction_count']
    list_filter = ['type', 'is_active']
    search_fields = ['name', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
