from django.contrib import admin
from .models import Notification, EmailLog


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'type', 'is_read', 'is_email_sent', 'created_at']
    list_filter = ['type', 'is_read', 'is_email_sent']
    search_fields = ['title', 'user__email']


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['subject', 'recipient', 'status', 'created_at', 'sent_at']
    list_filter = ['status']
    search_fields = ['subject', 'recipient']
