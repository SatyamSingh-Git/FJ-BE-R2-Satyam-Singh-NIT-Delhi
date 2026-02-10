"""
Tests for the bank_import app.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date

from .models import BankStatementImport, ImportedTransaction, CategorizationRule
from .views import auto_categorize_transaction, check_duplicate
from apps.categories.models import Category
from apps.transactions.models import Transaction


class CategorizationRuleTests(TestCase):
    """Test cases for categorization rules."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='ruleuser',
            email='rule@example.com',
            password='rulepass123'
        )
        Category.objects.filter(user=self.user).delete()
        self.category = Category.objects.create(
            user=self.user,
            name='Food',
            type='expense'
        )
    
    def test_rule_exact_match(self):
        """Test exact match categorization rule."""
        CategorizationRule.objects.create(
            user=self.user,
            keyword='SWIGGY ORDER',
            match_type='exact',
            category=self.category
        )
        
        result, confidence = auto_categorize_transaction('SWIGGY ORDER', self.user)
        self.assertEqual(result, self.category)
        self.assertEqual(confidence, Decimal('0.95'))
    
    def test_rule_contains_match(self):
        """Test contains match categorization rule."""
        CategorizationRule.objects.create(
            user=self.user,
            keyword='swiggy',
            match_type='contains',
            category=self.category
        )
        
        result, confidence = auto_categorize_transaction('Order from Swiggy App', self.user)
        self.assertEqual(result, self.category)
    
    def test_rule_starts_match(self):
        """Test starts with match categorization rule."""
        CategorizationRule.objects.create(
            user=self.user,
            keyword='UPI-',
            match_type='starts',
            category=self.category
        )
        
        result, confidence = auto_categorize_transaction('UPI-SWIGGY-12345', self.user)
        self.assertEqual(result, self.category)
    
    def test_default_keyword_mapping(self):
        """Test default keyword mapping for common transactions."""
        # Create expected category
        food_cat = Category.objects.create(
            user=self.user,
            name='Food & Dining',
            type='expense'
        )
        
        result, confidence = auto_categorize_transaction('Zomato Order #12345', self.user)
        self.assertEqual(result, food_cat)
        self.assertEqual(confidence, Decimal('0.7'))
    
    def test_no_match_returns_none(self):
        """Test that unrecognized descriptions return None."""
        result, confidence = auto_categorize_transaction('Random Unknown Transaction', self.user)
        self.assertIsNone(result)
        self.assertEqual(confidence, Decimal('0'))


class DuplicateDetectionTests(TestCase):
    """Test cases for duplicate transaction detection."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='dupuser',
            email='dup@example.com',
            password='duppass123'
        )
        Category.objects.filter(user=self.user).delete()
        self.category = Category.objects.create(
            user=self.user,
            name='Test',
            type='expense'
        )
    
    def test_exact_duplicate_detected(self):
        """Test that exact duplicates are detected."""
        Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('500.00'),
            date=date.today(),
            description='Pizza Hut Order'
        )
        
        is_dup = check_duplicate(date.today(), Decimal('500.00'), 'Pizza Hut Order', self.user)
        self.assertTrue(is_dup)
    
    def test_no_duplicate_different_amount(self):
        """Test that different amounts are not flagged as duplicates."""
        Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('500.00'),
            date=date.today(),
            description='Pizza Order'
        )
        
        is_dup = check_duplicate(date.today(), Decimal('600.00'), 'Pizza Order', self.user)
        self.assertFalse(is_dup)
    
    def test_duplicate_within_date_range(self):
        """Test duplicates detected within 3-day range."""
        from datetime import timedelta
        Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('500.00'),
            date=date.today() - timedelta(days=2),
            description='Test Transaction'
        )
        
        is_dup = check_duplicate(date.today(), Decimal('500.00'), 'Test Transaction', self.user)
        self.assertTrue(is_dup)


class BankImportViewTests(TestCase):
    """Test cases for bank import views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='importuser',
            email='import@example.com',
            password='importpass123'
        )
        self.client.login(username='importuser', password='importpass123')
    
    def test_import_list_view(self):
        """Test import list view loads."""
        response = self.client.get(reverse('bank_import:list'))
        self.assertEqual(response.status_code, 200)
    
    def test_upload_page_loads(self):
        """Test upload page loads."""
        response = self.client.get(reverse('bank_import:upload'))
        self.assertEqual(response.status_code, 200)
    
    def test_rules_page_loads(self):
        """Test categorization rules page loads."""
        response = self.client.get(reverse('bank_import:rules'))
        self.assertEqual(response.status_code, 200)
    
    def test_create_rule(self):
        """Test creating a categorization rule."""
        Category.objects.filter(user=self.user).delete()
        category = Category.objects.create(
            user=self.user,
            name='Test',
            type='expense'
        )
        
        response = self.client.post(reverse('bank_import:create_rule'), {
            'keyword': 'pizza',
            'match_type': 'contains',
            'category': category.id
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CategorizationRule.objects.filter(keyword='pizza').exists())
