"""
Tests for the categories app.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date

from .models import Category
from apps.transactions.models import Transaction


class CategoryModelTests(TestCase):
    """Test cases for Category model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='catuser',
            email='cat@example.com',
            password='catpass123'
        )
    
    def test_create_expense_category(self):
        """Test creating an expense category."""
        category = Category.objects.create(
            user=self.user,
            name='Food',
            type='expense',
            icon='🍔',
            color='#FF0000'
        )
        self.assertEqual(category.name, 'Food')
        self.assertEqual(category.type, 'expense')
    
    def test_create_income_category(self):
        """Test creating an income category."""
        category = Category.objects.create(
            user=self.user,
            name='Salary',
            type='income',
            icon='💼',
            color='#00FF00'
        )
        self.assertEqual(category.type, 'income')
    
    def test_category_str_representation(self):
        """Test the string representation of Category."""
        category = Category.objects.create(
            user=self.user,
            name='Shopping',
            type='expense',
            icon='🛒'
        )
        self.assertIn('Shopping', str(category))
        self.assertIn('🛒', str(category))
    
    def test_transaction_count_property(self):
        """Test the transaction_count property."""
        category = Category.objects.create(
            user=self.user,
            name='Test',
            type='expense'
        )
        self.assertEqual(category.transaction_count, 0)
        
        Transaction.objects.create(
            user=self.user,
            category=category,
            amount=Decimal('100.00'),
            date=date.today()
        )
        self.assertEqual(category.transaction_count, 1)
    
    def test_default_categories_creation(self):
        """Test creating default categories for a user."""
        new_user = User.objects.create_user(
            username='newuser',
            email='new@example.com',
            password='newpass123'
        )
        # Default categories are created via signal on user creation
        income_cats = Category.objects.filter(user=new_user, type='income')
        expense_cats = Category.objects.filter(user=new_user, type='expense')
        
        self.assertTrue(income_cats.exists())
        self.assertTrue(expense_cats.exists())
    
    def test_category_unique_constraint(self):
        """Test that duplicate category names of same type are not allowed."""
        Category.objects.create(
            user=self.user,
            name='Unique',
            type='expense'
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Category.objects.create(
                user=self.user,
                name='Unique',
                type='expense'
            )


class CategoryViewTests(TestCase):
    """Test cases for category views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='catviewuser',
            email='catview@example.com',
            password='catviewpass123'
        )
        self.client.login(username='catviewuser', password='catviewpass123')
        
        # Clear default categories for cleaner tests
        Category.objects.filter(user=self.user).delete()
        
        self.category = Category.objects.create(
            user=self.user,
            name='Test Category',
            type='expense',
            icon='📦',
            color='#4F46E5'
        )
    
    def test_category_list_view(self):
        """Test category list view loads."""
        response = self.client.get(reverse('categories:list'))
        self.assertEqual(response.status_code, 200)
    
    def test_category_create_view_get(self):
        """Test category create form loads."""
        response = self.client.get(reverse('categories:create'))
        self.assertEqual(response.status_code, 200)
    
    def test_category_create_view_post(self):
        """Test creating a category via POST."""
        response = self.client.post(reverse('categories:create'), {
            'name': 'New Category',
            'type': 'expense',
            'icon': '🎮',
            'color': '#FF0000',
            'description': 'Test description'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Category.objects.filter(name='New Category').exists())
    
    def test_category_create_duplicate_name(self):
        """Test that creating a duplicate category shows error."""
        response = self.client.post(reverse('categories:create'), {
            'name': 'Test Category',  # Same as existing
            'type': 'expense',
            'icon': '📦',
            'color': '#FF0000'
        })
        self.assertEqual(response.status_code, 200)  # Returns form with error
    
    def test_category_detail_view(self):
        """Test category detail view."""
        response = self.client.get(reverse('categories:detail', args=[self.category.pk]))
        self.assertEqual(response.status_code, 200)
    
    def test_category_update_view(self):
        """Test category update view."""
        response = self.client.post(
            reverse('categories:update', args=[self.category.pk]),
            {
                'name': 'Updated Name',
                'icon': '🎯',
                'color': '#00FF00',
                'description': 'Updated description',
                'is_active': 'on'
            }
        )
        self.assertEqual(response.status_code, 302)
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, 'Updated Name')
    
    def test_category_delete_with_transactions(self):
        """Test that category with transactions cannot be deleted."""
        Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('100.00'),
            date=date.today()
        )
        response = self.client.post(reverse('categories:delete', args=[self.category.pk]))
        # Should redirect with error message, category still exists
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())
    
    def test_category_delete_without_transactions(self):
        """Test that category without transactions can be deleted."""
        empty_category = Category.objects.create(
            user=self.user,
            name='Empty',
            type='expense'
        )
        response = self.client.post(reverse('categories:delete', args=[empty_category.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Category.objects.filter(pk=empty_category.pk).exists())
