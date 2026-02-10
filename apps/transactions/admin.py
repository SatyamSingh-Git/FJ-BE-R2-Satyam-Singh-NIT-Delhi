from django.contrib import admin
from .models import Transaction, RecurringTransaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['date', 'user', 'category', 'amount', 'currency', 'is_refund', 'is_imported']
    list_filter = ['category__type', 'currency', 'is_refund', 'is_imported', 'date']
    search_fields = ['description', 'user__email', 'category__name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'


@admin.register(RecurringTransaction)
class RecurringTransactionAdmin(admin.ModelAdmin):
    list_display = ['description', 'user', 'category', 'amount', 'frequency', 'is_active']
    list_filter = ['frequency', 'is_active']
    search_fields = ['description', 'user__email']
