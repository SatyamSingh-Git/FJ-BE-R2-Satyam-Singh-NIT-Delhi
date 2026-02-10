from django.db import models
from django.contrib.auth.models import User


class AIInsight(models.Model):
    """AI-generated financial insights."""
    
    INSIGHT_TYPES = [
        ('spending_analysis', 'Spending Analysis'),
        ('savings_tip', 'Savings Tip'),
        ('anomaly_alert', 'Anomaly Alert'),
        ('budget_recommendation', 'Budget Recommendation'),
        ('category_suggestion', 'Category Suggestion'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_insights')
    type = models.CharField(max_length=25, choices=INSIGHT_TYPES)
    title = models.CharField(max_length=255)
    content = models.TextField()
    
    # Related transaction if applicable
    transaction_id = models.IntegerField(null=True, blank=True)
    
    is_dismissed = models.BooleanField(default=False)
    is_helpful = models.BooleanField(null=True, blank=True)  # User feedback
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'AI Insight'
        verbose_name_plural = 'AI Insights'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.email}"


class SpendingAnomaly(models.Model):
    """Detected spending anomalies."""
    
    ANOMALY_TYPES = [
        ('unusual_amount', 'Unusual Amount'),
        ('unusual_category', 'Unusual Category'),
        ('unusual_frequency', 'Unusual Frequency'),
        ('duplicate', 'Possible Duplicate'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='anomalies')
    transaction = models.ForeignKey(
        'transactions.Transaction', 
        on_delete=models.CASCADE,
        related_name='anomalies'
    )
    
    type = models.CharField(max_length=20, choices=ANOMALY_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS, default='medium')
    description = models.TextField()
    
    # Statistical context
    expected_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    deviation_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    is_reviewed = models.BooleanField(default=False)
    is_false_positive = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Spending Anomaly'
        verbose_name_plural = 'Spending Anomalies'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.transaction}"


class ChatHistory(models.Model):
    """Store chat history with AI assistant."""
    
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_history')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Chat Message'
        verbose_name_plural = 'Chat History'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."
