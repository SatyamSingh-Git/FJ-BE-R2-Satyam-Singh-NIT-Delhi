from django.contrib import admin
from .models import Budget


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['category', 'user', 'amount', 'period', 'spent_percentage', 'is_active']
    list_filter = ['period', 'is_active', 'category__type']
    search_fields = ['category__name', 'user__email']
    readonly_fields = ['created_at', 'updated_at', 'spent', 'remaining', 'spent_percentage']
