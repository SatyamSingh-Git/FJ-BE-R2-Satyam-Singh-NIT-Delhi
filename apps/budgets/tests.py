"""
Tests for the budgets app.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date, timedelta

from .models import Budget
from apps.categories.models import Category
from apps.transactions.models import Transaction


class BudgetModelTests(TestCase):
    """Test cases for Budget model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='budgetuser',
            email='budget@example.com',
            password='budgetpass123'
        )
        self.category = Category.objects.create(
            user=self.user,
            name='Food',
            type='expense',
            icon='🍔',
            color='#FF0000'
        )
    
    def test_create_budget(self):
        """Test creating a budget."""
        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('5000.00'),
            period='monthly',
            start_date=date.today().replace(day=1)
        )
        self.assertEqual(budget.amount, Decimal('5000.00'))
        self.assertEqual(budget.period, 'monthly')
    
    def test_spent_property_no_transactions(self):
        """Test spent property with no transactions."""
        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('5000.00'),
            period='monthly',
            start_date=date.today().replace(day=1)
        )
        self.assertEqual(budget.spent, Decimal('0.00'))
    
    def test_spent_property_with_transactions(self):
        """Test spent property with transactions."""
        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('5000.00'),
            period='monthly',
            start_date=date.today().replace(day=1)
        )
        Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('1000.00'),
            date=date.today()
        )
        Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('500.00'),
            date=date.today()
        )
        self.assertEqual(budget.spent, Decimal('1500.00'))
    
    def test_remaining_property(self):
        """Test remaining budget property."""
        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('5000.00'),
            period='monthly',
            start_date=date.today().replace(day=1)
        )
        Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('3000.00'),
            date=date.today()
        )
        self.assertEqual(budget.remaining, Decimal('2000.00'))
    
    def test_spent_percentage(self):
        """Test spent percentage calculation."""
        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('1000.00'),
            period='monthly',
            start_date=date.today().replace(day=1)
        )
        Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('800.00'),
            date=date.today()
        )
        self.assertEqual(budget.spent_percentage, 80.0)
    
    def test_is_over_budget(self):
        """Test over budget detection."""
        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('1000.00'),
            period='monthly',
            start_date=date.today().replace(day=1)
        )
        Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('1200.00'),
            date=date.today()
        )
        self.assertTrue(budget.is_over_budget)
    
    def test_should_alert(self):
        """Test should_alert property."""
        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('1000.00'),
            period='monthly',
            start_date=date.today().replace(day=1),
            alert_at_percentage=80
        )
        Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('850.00'),
            date=date.today()
        )
        self.assertTrue(budget.should_alert)
    
    def test_get_status(self):
        """Test get_status method."""
        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('1000.00'),
            period='monthly',
            start_date=date.today().replace(day=1)
        )
        status = budget.get_status()
        self.assertEqual(status['status'], 'good')
        self.assertEqual(status['color'], 'green')
    
    def test_refunds_not_counted_in_spent(self):
        """Test that refunds are not counted in spent amount."""
        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('1000.00'),
            period='monthly',
            start_date=date.today().replace(day=1)
        )
        Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('500.00'),
            date=date.today()
        )
        Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('100.00'),
            date=date.today(),
            is_refund=True
        )
        self.assertEqual(budget.spent, Decimal('500.00'))


class BudgetViewTests(TestCase):
    """Test cases for budget views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='budgetviewuser',
            email='budgetview@example.com',
            password='budgetviewpass123'
        )
        self.client.login(username='budgetviewuser', password='budgetviewpass123')
        
        # Clear default categories and create one
        Category.objects.filter(user=self.user).delete()
        self.category = Category.objects.create(
            user=self.user,
            name='Test Category',
            type='expense'
        )
    
    def test_budget_list_view(self):
        """Test budget list view loads."""
        response = self.client.get(reverse('budgets:list'))
        self.assertEqual(response.status_code, 200)
    
    def test_budget_create_view_get(self):
        """Test budget create form loads."""
        response = self.client.get(reverse('budgets:create'))
        self.assertEqual(response.status_code, 200)
    
    def test_budget_create_view_post(self):
        """Test creating a budget via POST."""
        response = self.client.post(reverse('budgets:create'), {
            'category': self.category.id,
            'amount': '5000.00',
            'period': 'monthly',
            'start_date': date.today().isoformat(),
            'alert_threshold': 80
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Budget.objects.filter(category=self.category).exists())
    
    def test_budget_detail_view(self):
        """Test budget detail view."""
        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('5000.00'),
            period='monthly',
            start_date=date.today()
        )
        response = self.client.get(reverse('budgets:detail', args=[budget.pk]))
        self.assertEqual(response.status_code, 200)
    
    def test_budget_update_view(self):
        """Test budget update view."""
        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('5000.00'),
            period='monthly',
            start_date=date.today()
        )
        response = self.client.post(
            reverse('budgets:update', args=[budget.pk]),
            {'amount': '6000.00', 'alert_threshold': 75, 'is_active': 'on'}
        )
        self.assertEqual(response.status_code, 302)
        budget.refresh_from_db()
        self.assertEqual(budget.amount, Decimal('6000.00'))
    
    def test_budget_delete_view(self):
        """Test budget delete view."""
        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('5000.00'),
            period='monthly',
            start_date=date.today()
        )
        response = self.client.post(reverse('budgets:delete', args=[budget.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Budget.objects.filter(pk=budget.pk).exists())
    
    def test_duplicate_active_budget_prevented(self):
        """Test that duplicate active budgets for same category are prevented."""
        Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('5000.00'),
            period='monthly',
            start_date=date.today(),
            is_active=True
        )
        response = self.client.post(reverse('budgets:create'), {
            'category': self.category.id,
            'amount': '3000.00',
            'period': 'monthly',
            'start_date': date.today().isoformat(),
            'alert_threshold': 80
        })
        # Should return form with error
        self.assertEqual(response.status_code, 200)
