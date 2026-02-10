from django.db import models
from django.contrib.auth.models import User


class BankStatementImport(models.Model):
    """Track imported bank statements."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    FILE_TYPES = [
        ('pdf', 'PDF'),
        ('csv', 'CSV'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bank_imports')
    file = models.FileField(upload_to='bank_statements/%Y/%m/')
    file_type = models.CharField(max_length=5, choices=FILE_TYPES)
    file_name = models.CharField(max_length=255)
    
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    
    # Import statistics
    total_transactions = models.IntegerField(default=0)
    imported_count = models.IntegerField(default=0)
    duplicate_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Bank Statement Import'
        verbose_name_plural = 'Bank Statement Imports'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.file_name} - {self.status}"


class ImportedTransaction(models.Model):
    """Temporarily store parsed transactions before confirmation."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('duplicate', 'Duplicate'),
    ]
    
    import_batch = models.ForeignKey(
        BankStatementImport, 
        on_delete=models.CASCADE,
        related_name='parsed_transactions'
    )
    
    # Parsed data
    date = models.DateField()
    description = models.TextField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    transaction_type = models.CharField(max_length=10)  # credit/debit
    
    # Auto-categorization
    suggested_category = models.ForeignKey(
        'categories.Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suggested_imports'
    )
    confidence_score = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    
    # Reference for duplicate detection
    external_reference = models.CharField(max_length=255, blank=True)
    
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    
    # Link to created transaction after approval
    created_transaction = models.ForeignKey(
        'transactions.Transaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='import_source'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Imported Transaction'
        verbose_name_plural = 'Imported Transactions'
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.date} - {self.description[:30]} - {self.amount}"


class CategorizationRule(models.Model):
    """Rules for auto-categorizing transactions."""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categorization_rules')
    
    # Matching criteria
    keyword = models.CharField(max_length=255)
    match_type = models.CharField(
        max_length=10,
        choices=[('contains', 'Contains'), ('exact', 'Exact Match'), ('starts', 'Starts With')],
        default='contains'
    )
    
    # Target category
    category = models.ForeignKey(
        'categories.Category',
        on_delete=models.CASCADE,
        related_name='categorization_rules'
    )
    
    is_active = models.BooleanField(default=True)
    match_count = models.IntegerField(default=0)  # Track usage
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Categorization Rule'
        verbose_name_plural = 'Categorization Rules'
        ordering = ['-match_count']
    
    def __str__(self):
        return f"'{self.keyword}' -> {self.category.name}"
