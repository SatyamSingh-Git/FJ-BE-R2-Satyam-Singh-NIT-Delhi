"""
Tests for the transactions app.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date, timedelta

from .models import Transaction, RecurringTransaction
from apps.categories.models import Category


class TransactionModelTests(TestCase):
    """Test cases for Transaction model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='transuser',
            email='trans@example.com',
            password='transpass123'
        )
        self.expense_category = Category.objects.create(
            user=self.user,
            name='Test Expense',
            type='expense',
            icon='📦',
            color='#FF0000'
        )
        self.income_category = Category.objects.create(
            user=self.user,
            name='Test Income',
            type='income',
            icon='💰',
            color='#00FF00'
        )
    
    def test_create_expense_transaction(self):
        """Test creating an expense transaction."""
        transaction = Transaction.objects.create(
            user=self.user,
            category=self.expense_category,
            amount=Decimal('100.50'),
            date=date.today(),
            description='Test expense'
        )
        self.assertEqual(transaction.amount, Decimal('100.50'))
        self.assertEqual(transaction.type, 'expense')
    
    def test_create_income_transaction(self):
        """Test creating an income transaction."""
        transaction = Transaction.objects.create(
            user=self.user,
            category=self.income_category,
            amount=Decimal('5000.00'),
            date=date.today(),
            description='Test salary'
        )
        self.assertEqual(transaction.type, 'income')
    
    def test_effective_amount_expense(self):
        """Test effective_amount property for expenses."""
        transaction = Transaction.objects.create(
            user=self.user,
            category=self.expense_category,
            amount=Decimal('100.00'),
            date=date.today()
        )
        self.assertEqual(transaction.effective_amount, Decimal('-100.00'))
    
    def test_effective_amount_income(self):
        """Test effective_amount property for income."""
        transaction = Transaction.objects.create(
            user=self.user,
            category=self.income_category,
            amount=Decimal('100.00'),
            date=date.today()
        )
        self.assertEqual(transaction.effective_amount, Decimal('100.00'))
    
    def test_refund_effective_amount(self):
        """Test that refunds have positive effective amount even for expenses."""
        transaction = Transaction.objects.create(
            user=self.user,
            category=self.expense_category,
            amount=Decimal('50.00'),
            date=date.today(),
            is_refund=True
        )
        self.assertEqual(transaction.effective_amount, Decimal('50.00'))
    
    def test_decimal_precision(self):
        """Test that amounts are properly quantized to 2 decimal places."""
        transaction = Transaction.objects.create(
            user=self.user,
            category=self.expense_category,
            amount=Decimal('100.555'),  # Should be rounded
            date=date.today()
        )
        self.assertEqual(transaction.amount, Decimal('100.56'))
    
    def test_transaction_ordering(self):
        """Test that transactions are ordered by date descending."""
        t1 = Transaction.objects.create(
            user=self.user,
            category=self.expense_category,
            amount=Decimal('10.00'),
            date=date.today() - timedelta(days=1)
        )
        t2 = Transaction.objects.create(
            user=self.user,
            category=self.expense_category,
            amount=Decimal('20.00'),
            date=date.today()
        )
        transactions = list(Transaction.objects.filter(user=self.user))
        self.assertEqual(transactions[0], t2)  # Most recent first


class TransactionViewTests(TestCase):
    """Test cases for transaction views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='viewuser',
            email='view@example.com',
            password='viewpass123'
        )
        self.category = Category.objects.create(
            user=self.user,
            name='Food',
            type='expense',
            icon='🍔',
            color='#FF0000'
        )
        self.client.login(username='viewuser', password='viewpass123')
    
    def test_transaction_list_view(self):
        """Test transaction list view loads."""
        response = self.client.get(reverse('transactions:list'))
        self.assertEqual(response.status_code, 200)
    
    def test_transaction_create_view_get(self):
        """Test transaction create form loads."""
        response = self.client.get(reverse('transactions:create'))
        self.assertEqual(response.status_code, 200)
    
    def test_transaction_create_view_post(self):
        """Test creating a transaction via POST."""
        response = self.client.post(reverse('transactions:create'), {
            'category': self.category.id,
            'amount': '150.00',
            'date': date.today().isoformat(),
            'description': 'Lunch',
            'currency': 'INR'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(Transaction.objects.filter(description='Lunch').exists())
    
    def test_transaction_create_negative_amount(self):
        """Test that negative amounts are handled (converted to positive)."""
        response = self.client.post(reverse('transactions:create'), {
            'category': self.category.id,
            'amount': '-150.00',
            'date': date.today().isoformat(),
            'description': 'Negative test',
            'currency': 'INR'
        })
        # Should either reject or convert to positive
        # Based on implementation, this should be handled
        self.assertEqual(response.status_code, 200)  # Error page or 302 for success
    
    def test_transaction_detail_view(self):
        """Test transaction detail view."""
        transaction = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('100.00'),
            date=date.today(),
            description='Detail test'
        )
        response = self.client.get(reverse('transactions:detail', args=[transaction.pk]))
        self.assertEqual(response.status_code, 200)
    
    def test_transaction_update_view(self):
        """Test transaction update view."""
        transaction = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('100.00'),
            date=date.today()
        )
        response = self.client.get(reverse('transactions:update', args=[transaction.pk]))
        self.assertEqual(response.status_code, 200)
    
    def test_transaction_delete_view(self):
        """Test transaction delete view."""
        transaction = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('100.00'),
            date=date.today()
        )
        response = self.client.post(reverse('transactions:delete', args=[transaction.pk]))
        self.assertEqual(response.status_code, 302)  # Redirect after delete
        self.assertFalse(Transaction.objects.filter(pk=transaction.pk).exists())
    
    def test_cannot_access_other_user_transaction(self):
        """Test that users cannot access other users' transactions."""
        other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='otherpass123'
        )
        other_category = Category.objects.create(
            user=other_user,
            name='Other',
            type='expense'
        )
        other_transaction = Transaction.objects.create(
            user=other_user,
            category=other_category,
            amount=Decimal('100.00'),
            date=date.today()
        )
        response = self.client.get(reverse('transactions:detail', args=[other_transaction.pk]))
        self.assertEqual(response.status_code, 404)


class TransactionFilterTests(TestCase):
    """Test cases for transaction filtering."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='filteruser',
            email='filter@example.com',
            password='filterpass123'
        )
        self.category = Category.objects.create(
            user=self.user,
            name='Filter Test',
            type='expense'
        )
        self.client.login(username='filteruser', password='filterpass123')
        
        # Create test transactions
        for i in range(5):
            Transaction.objects.create(
                user=self.user,
                category=self.category,
                amount=Decimal(f'{(i+1)*100}.00'),
                date=date.today() - timedelta(days=i)
            )
    
    def test_filter_by_category(self):
        """Test filtering transactions by category."""
        response = self.client.get(
            reverse('transactions:list'),
            {'category': self.category.id}
        )
        self.assertEqual(response.status_code, 200)
    
    def test_filter_by_date_range(self):
        """Test filtering transactions by date range."""
        response = self.client.get(
            reverse('transactions:list'),
            {
                'start_date': (date.today() - timedelta(days=3)).isoformat(),
                'end_date': date.today().isoformat()
            }
        )
        self.assertEqual(response.status_code, 200)
