from django.contrib import admin
from .models import BankStatementImport, ImportedTransaction, CategorizationRule


@admin.register(BankStatementImport)
class BankStatementImportAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'user', 'file_type', 'status', 'total_transactions', 
                    'imported_count', 'duplicate_count', 'created_at']
    list_filter = ['status', 'file_type']
    search_fields = ['file_name', 'user__email']


@admin.register(ImportedTransaction)
class ImportedTransactionAdmin(admin.ModelAdmin):
    list_display = ['date', 'description', 'amount', 'transaction_type', 
                    'suggested_category', 'status']
    list_filter = ['status', 'transaction_type']
    search_fields = ['description']


@admin.register(CategorizationRule)
class CategorizationRuleAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'category', 'user', 'match_type', 'match_count', 'is_active']
    list_filter = ['match_type', 'is_active']
    search_fields = ['keyword', 'category__name']
