from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum
from decimal import Decimal
from datetime import date
from apps.categories.models import Category


class Budget(models.Model):
    """Budget goal for a category."""
    
    PERIOD_CHOICES = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='budgets')
    
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES, default='monthly')
    
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    # Alert settings
    alert_at_percentage = models.IntegerField(default=80)
    alert_sent = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Budget'
        verbose_name_plural = 'Budgets'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.category.name} Budget: {self.currency} {self.amount}/{self.period}"
    
    @property
    def spent(self):
        """Calculate total spent in this budget period."""
        from apps.transactions.models import Transaction
        
        end = self.end_date or date.today()
        transactions = Transaction.objects.filter(
            user=self.user,
            category=self.category,
            date__gte=self.start_date,
            date__lte=end,
            is_refund=False
        ).aggregate(total=Sum('amount'))
        
        return transactions['total'] or Decimal('0.00')
    
    @property
    def remaining(self):
        """Calculate remaining budget."""
        return max(self.amount - self.spent, Decimal('0.00'))
    
    @property
    def spent_percentage(self):
        """Calculate percentage of budget spent."""
        if self.amount == 0:
            return 0
        return min(round((self.spent / self.amount) * 100, 1), 100)
    
    @property
    def is_over_budget(self):
        """Check if spending exceeded the budget."""
        return self.spent > self.amount
    
    @property
    def should_alert(self):
        """Check if we should send an alert."""
        return self.spent_percentage >= self.alert_at_percentage and not self.alert_sent
    
    def get_status(self):
        """Get budget status with color coding."""
        percentage = self.spent_percentage
        if percentage >= 100:
            return {'status': 'over', 'color': 'red', 'message': 'Over Budget!'}
        elif percentage >= 90:
            return {'status': 'critical', 'color': 'orange', 'message': 'Almost at limit'}
        elif percentage >= 75:
            return {'status': 'warning', 'color': 'yellow', 'message': 'Getting close'}
        else:
            return {'status': 'good', 'color': 'green', 'message': 'On track'}
