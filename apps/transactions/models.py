from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
from apps.categories.models import Category


class Transaction(models.Model):
    """Financial transaction - income or expense."""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    category = models.ForeignKey(
        Category, 
        on_delete=models.PROTECT,  # Prevent deletion of category with transactions
        related_name='transactions'
    )
    
    # Amount with proper decimal precision
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Currency support
    currency = models.CharField(max_length=3, default='INR')
    
    # Transaction details
    date = models.DateField()
    description = models.TextField(blank=True)
    
    # For refunds/negative amounts in expense categories
    is_refund = models.BooleanField(default=False)
    
    # Receipt upload
    receipt = models.ImageField(upload_to='receipts/%Y/%m/', blank=True, null=True)
    
    # For bank import feature - duplicate detection
    external_id = models.CharField(max_length=255, blank=True, null=True)  # Bank transaction ID
    is_imported = models.BooleanField(default=False)
    
    # Metadata
    notes = models.TextField(blank=True)
    tags = models.CharField(max_length=255, blank=True)  # Comma-separated tags
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['user', 'category']),
            models.Index(fields=['user', 'date', 'category']),
        ]
    
    def __str__(self):
        type_str = "Refund" if self.is_refund else self.category.get_type_display()
        return f"{self.date} - {self.category.name}: {self.currency} {self.amount} ({type_str})"
    
    @property
    def effective_amount(self):
        """Returns negative amount for expenses, positive for income."""
        if self.category.type == 'expense' and not self.is_refund:
            return -self.amount
        return self.amount
    
    @property
    def type(self):
        """Get the transaction type from category."""
        return self.category.type
    
    def save(self, *args, **kwargs):
        # Ensure amount has 2 decimal places
        self.amount = Decimal(str(self.amount)).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)


class RecurringTransaction(models.Model):
    """Template for recurring transactions (subscriptions, salary, etc.)."""
    
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recurring_transactions')
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    description = models.TextField(blank=True)
    
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    last_generated = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Recurring Transaction'
        verbose_name_plural = 'Recurring Transactions'
    
    def __str__(self):
        return f"{self.description} - {self.frequency} {self.currency} {self.amount}"
