from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    """Category for organizing income and expenses."""
    
    CATEGORY_TYPES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]
    
    ICON_CHOICES = [
        ('💰', 'Money'),
        ('💼', 'Work'),
        ('🏠', 'Home'),
        ('🍔', 'Food'),
        ('🚗', 'Transport'),
        ('🎮', 'Entertainment'),
        ('🏥', 'Health'),
        ('📚', 'Education'),
        ('🛒', 'Shopping'),
        ('✈️', 'Travel'),
        ('💡', 'Utilities'),
        ('📱', 'Phone'),
        ('🎁', 'Gifts'),
        ('💳', 'Subscriptions'),
        ('📈', 'Investments'),
        ('🏦', 'Banking'),
        ('👨‍👩‍👧', 'Family'),
        ('🐕', 'Pets'),
        ('💇', 'Personal Care'),
        ('📦', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=CATEGORY_TYPES)
    icon = models.CharField(max_length=10, choices=ICON_CHOICES, default='📦')
    color = models.CharField(max_length=7, default='#4F46E5')  # Hex color
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        unique_together = ['user', 'name', 'type']
        ordering = ['type', 'name']
    
    def __str__(self):
        return f"{self.icon} {self.name} ({self.get_type_display()})"
    
    @property
    def transaction_count(self):
        """Get the number of transactions in this category."""
        return self.transactions.count()
    
    @classmethod
    def create_default_categories(cls, user):
        """Create default categories for a new user."""
        default_income = [
            ('Salary', '💼', '#10B981'),
            ('Freelance', '💻', '#3B82F6'),
            ('Investments', '📈', '#8B5CF6'),
            ('Gifts', '🎁', '#EC4899'),
            ('Other Income', '💰', '#6366F1'),
        ]
        
        default_expense = [
            ('Food & Dining', '🍔', '#EF4444'),
            ('Transport', '🚗', '#F59E0B'),
            ('Shopping', '🛒', '#8B5CF6'),
            ('Entertainment', '🎮', '#EC4899'),
            ('Bills & Utilities', '💡', '#6366F1'),
            ('Health', '🏥', '#10B981'),
            ('Education', '📚', '#3B82F6'),
            ('Travel', '✈️', '#14B8A6'),
            ('Subscriptions', '💳', '#F97316'),
            ('Other Expenses', '📦', '#6B7280'),
        ]
        
        categories = []
        for name, icon, color in default_income:
            categories.append(cls(user=user, name=name, type='income', icon=icon, color=color))
        
        for name, icon, color in default_expense:
            categories.append(cls(user=user, name=name, type='expense', icon=icon, color=color))
        
        cls.objects.bulk_create(categories, ignore_conflicts=True)
