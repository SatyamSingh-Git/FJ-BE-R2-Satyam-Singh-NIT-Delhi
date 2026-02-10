from django.contrib import admin
from .models import AIInsight, SpendingAnomaly, ChatHistory


@admin.register(AIInsight)
class AIInsightAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'type', 'is_dismissed', 'created_at']
    list_filter = ['type', 'is_dismissed', 'is_helpful']
    search_fields = ['title', 'user__email']


@admin.register(SpendingAnomaly)
class SpendingAnomalyAdmin(admin.ModelAdmin):
    list_display = ['transaction', 'user', 'type', 'severity', 'is_reviewed', 'created_at']
    list_filter = ['type', 'severity', 'is_reviewed', 'is_false_positive']
    search_fields = ['user__email']


@admin.register(ChatHistory)
class ChatHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'content_preview', 'created_at']
    list_filter = ['role']
    search_fields = ['user__email', 'content']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
