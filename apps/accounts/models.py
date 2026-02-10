from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """Extended user profile with finance-specific settings."""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=15, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    preferred_currency = models.CharField(max_length=3, default='INR')
    
    # Notification preferences
    email_notifications = models.BooleanField(default=True)
    budget_alert_threshold = models.IntegerField(default=80)  # Alert at 80% of budget
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f"{self.user.email}'s Profile"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically create a profile and default categories when a new user is created."""
    if created:
        UserProfile.objects.create(user=instance)
        # Create default categories for new user
        from apps.categories.models import Category
        Category.create_default_categories(instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the profile whenever the user is saved."""
    if hasattr(instance, 'profile'):
        instance.profile.save()
