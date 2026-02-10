"""
Tests for the accounts app.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import UserProfile
from apps.categories.models import Category


class UserProfileTests(TestCase):
    """Test cases for UserProfile model and signals."""
    
    def test_profile_created_on_user_creation(self):
        """Test that a UserProfile is automatically created when a User is created."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsInstance(user.profile, UserProfile)
    
    def test_default_categories_created(self):
        """Test that default categories are created for new users."""
        user = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        categories = Category.objects.filter(user=user)
        # Should have default income and expense categories
        self.assertTrue(categories.exists())
        self.assertTrue(categories.filter(type='income').exists())
        self.assertTrue(categories.filter(type='expense').exists())
    
    def test_profile_default_values(self):
        """Test that profile has correct default values."""
        user = User.objects.create_user(
            username='testuser3',
            email='test3@example.com',
            password='testpass123'
        )
        profile = user.profile
        self.assertEqual(profile.preferred_currency, 'INR')
        self.assertTrue(profile.email_notifications)
        self.assertEqual(profile.budget_alert_threshold, 80)
    
    def test_profile_str_representation(self):
        """Test the string representation of UserProfile."""
        user = User.objects.create_user(
            username='testuser4',
            email='test4@example.com',
            password='testpass123'
        )
        self.assertEqual(str(user.profile), "test4@example.com's Profile")


class AuthenticationViewTests(TestCase):
    """Test cases for authentication views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='authuser',
            email='auth@example.com',
            password='authpass123'
        )
    
    def test_home_page_loads(self):
        """Test that the home page loads for unauthenticated users."""
        response = self.client.get(reverse('accounts:home'))
        self.assertEqual(response.status_code, 200)
    
    def test_home_redirects_authenticated_user(self):
        """Test that authenticated users are redirected from home to dashboard."""
        self.client.login(username='authuser', password='authpass123')
        response = self.client.get(reverse('accounts:home'))
        self.assertRedirects(response, reverse('accounts:dashboard'))
    
    def test_dashboard_requires_login(self):
        """Test that dashboard requires authentication."""
        response = self.client.get(reverse('accounts:dashboard'))
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
    
    def test_dashboard_loads_for_authenticated_user(self):
        """Test that dashboard loads for authenticated users."""
        self.client.login(username='authuser', password='authpass123')
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(response.status_code, 200)
    
    def test_profile_requires_login(self):
        """Test that profile page requires authentication."""
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 302)
    
    def test_profile_loads(self):
        """Test that profile page loads for authenticated users."""
        self.client.login(username='authuser', password='authpass123')
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)


class ProfileUpdateTests(TestCase):
    """Test cases for profile update functionality."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='updateuser',
            email='update@example.com',
            password='updatepass123'
        )
        self.client.login(username='updateuser', password='updatepass123')
    
    def test_profile_update_page_loads(self):
        """Test that profile update page loads."""
        response = self.client.get(reverse('accounts:profile_update'))
        self.assertEqual(response.status_code, 200)
    
    def test_profile_update_first_name(self):
        """Test updating first name."""
        response = self.client.post(reverse('accounts:profile_update'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'phone': '',
            'preferred_currency': 'INR',
            'budget_alert_threshold': 80
        })
        self.assertRedirects(response, reverse('accounts:profile'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'John')
        self.assertEqual(self.user.last_name, 'Doe')
    
    def test_profile_update_currency(self):
        """Test updating preferred currency."""
        response = self.client.post(reverse('accounts:profile_update'), {
            'first_name': '',
            'last_name': '',
            'phone': '',
            'preferred_currency': 'USD',
            'budget_alert_threshold': 75
        })
        self.assertRedirects(response, reverse('accounts:profile'))
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.preferred_currency, 'USD')
        self.assertEqual(self.user.profile.budget_alert_threshold, 75)
