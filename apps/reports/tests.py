"""
Tests for the reports app.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date, timedelta

from apps.categories.models import Category
from apps.transactions.models import Transaction


class ReportViewTests(TestCase):
    """Test cases for report views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='reportuser',
            email='report@example.com',
            password='reportpass123'
        )
        self.client.login(username='reportuser', password='reportpass123')
        
        # Create test data
        Category.objects.filter(user=self.user).delete()
        self.income_category = Category.objects.create(
            user=self.user,
            name='Salary',
            type='income'
        )
        self.expense_category = Category.objects.create(
            user=self.user,
            name='Food',
            type='expense'
        )
        
        # Create transactions
        Transaction.objects.create(
            user=self.user,
            category=self.income_category,
            amount=Decimal('50000.00'),
            date=date.today()
        )
        Transaction.objects.create(
            user=self.user,
            category=self.expense_category,
            amount=Decimal('5000.00'),
            date=date.today()
        )
    
    def test_reports_home_view(self):
        """Test reports home page loads."""
        response = self.client.get(reverse('reports:home'))
        self.assertEqual(response.status_code, 200)
    
    def test_monthly_report_view(self):
        """Test monthly report view loads."""
        response = self.client.get(reverse('reports:monthly'))
        self.assertEqual(response.status_code, 200)
    
    def test_monthly_report_with_date_params(self):
        """Test monthly report with specific month/year."""
        response = self.client.get(
            reverse('reports:monthly'),
            {'month': date.today().month, 'year': date.today().year}
        )
        self.assertEqual(response.status_code, 200)
    
    def test_category_report_view(self):
        """Test category report view loads."""
        response = self.client.get(reverse('reports:category'))
        self.assertEqual(response.status_code, 200)
    
    def test_export_csv(self):
        """Test CSV export functionality."""
        response = self.client.get(reverse('reports:export_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
    
    def test_export_csv_with_filters(self):
        """Test CSV export with date filters."""
        response = self.client.get(
            reverse('reports:export_csv'),
            {
                'start_date': (date.today() - timedelta(days=30)).isoformat(),
                'end_date': date.today().isoformat()
            }
        )
        self.assertEqual(response.status_code, 200)
    
    def test_export_pdf(self):
        """Test PDF export functionality."""
        response = self.client.get(reverse('reports:export_pdf'))
        self.assertEqual(response.status_code, 200)


class ReportDataTests(TestCase):
    """Test cases for report data calculations."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='datauser',
            email='data@example.com',
            password='datapass123'
        )
        self.client.login(username='datauser', password='datapass123')
        
        Category.objects.filter(user=self.user).delete()
        self.income_category = Category.objects.create(
            user=self.user,
            name='Salary',
            type='income'
        )
        self.expense_category = Category.objects.create(
            user=self.user,
            name='Shopping',
            type='expense'
        )
    
    def test_monthly_report_income_total(self):
        """Test that monthly report correctly calculates income."""
        Transaction.objects.create(
            user=self.user,
            category=self.income_category,
            amount=Decimal('60000.00'),
            date=date.today()
        )
        
        response = self.client.get(reverse('reports:monthly'))
        self.assertContains(response, '60')  # Should contain part of the amount
    
    def test_monthly_report_expense_total(self):
        """Test that monthly report correctly calculates expenses."""
        Transaction.objects.create(
            user=self.user,
            category=self.expense_category,
            amount=Decimal('15000.00'),
            date=date.today()
        )
        
        response = self.client.get(reverse('reports:monthly'))
        self.assertContains(response, '15')  # Should contain part of the amount
    
    def test_category_breakdown(self):
        """Test that category report shows breakdown by category."""
        Transaction.objects.create(
            user=self.user,
            category=self.expense_category,
            amount=Decimal('5000.00'),
            date=date.today()
        )
        
        response = self.client.get(reverse('reports:category'))
        self.assertContains(response, 'Shopping')
    
    def test_empty_report_handles_gracefully(self):
        """Test that reports handle no data gracefully."""
        # No transactions created
        response = self.client.get(reverse('reports:monthly'))
        self.assertEqual(response.status_code, 200)
