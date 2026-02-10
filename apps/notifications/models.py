from django.db import models
from django.contrib.auth.models import User


class Notification(models.Model):
    """User notifications for budget alerts, anomalies, etc."""
    
    NOTIFICATION_TYPES = [
        ('budget_warning', 'Budget Warning'),
        ('budget_exceeded', 'Budget Exceeded'),
        ('anomaly_detected', 'Anomaly Detected'),
        ('weekly_summary', 'Weekly Summary'),
        ('monthly_report', 'Monthly Report'),
        ('system', 'System Notification'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # Related objects
    budget_id = models.IntegerField(null=True, blank=True)
    transaction_id = models.IntegerField(null=True, blank=True)
    
    is_read = models.BooleanField(default=False)
    is_email_sent = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.email}"
    
    def mark_as_read(self):
        self.is_read = True
        self.save(update_fields=['is_read'])


class EmailLog(models.Model):
    """Log of sent emails for tracking."""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_logs')
    subject = models.CharField(max_length=255)
    recipient = models.EmailField()
    status = models.CharField(max_length=20, default='pending')  # pending, sent, failed
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.subject} to {self.recipient} - {self.status}"
