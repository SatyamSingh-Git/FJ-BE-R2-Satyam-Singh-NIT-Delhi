from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from datetime import datetime

from .models import Notification, EmailLog


@login_required
def notification_list(request):
    """List all notifications."""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    unread_count = notifications.filter(is_read=False).count()
    
    context = {
        'notifications': notifications[:50],
        'unread_count': unread_count,
    }
    return render(request, 'notifications/list.html', context)


@login_required
def mark_read(request, pk):
    """Mark a notification as read."""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.mark_as_read()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('notifications:list')


@login_required
def mark_all_read(request):
    """Mark all notifications as read."""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, 'All notifications marked as read.')
    return redirect('notifications:list')


@login_required
def notification_settings(request):
    """Update notification preferences."""
    profile = request.user.profile
    
    if request.method == 'POST':
        profile.email_notifications = request.POST.get('email_notifications') == 'on'
        profile.budget_alert_threshold = int(request.POST.get('budget_alert_threshold', 80))
        profile.save()
        messages.success(request, 'Notification settings updated.')
        return redirect('accounts:profile')
    
    context = {
        'profile': profile,
    }
    return render(request, 'notifications/settings.html', context)


def send_budget_alert(user, budget):
    """Send email notification for budget alert."""
    if not user.profile.email_notifications:
        return False
    
    subject = f"Budget Alert: {budget.category.name}"
    
    html_message = render_to_string('notifications/email/budget_alert.html', {
        'user': user,
        'budget': budget,
        'spent_percentage': budget.spent_percentage,
    })
    
    try:
        send_mail(
            subject=subject,
            message=f"You've spent {budget.spent_percentage}% of your {budget.category.name} budget.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        # Log the email
        EmailLog.objects.create(
            user=user,
            subject=subject,
            recipient=user.email,
            status='sent',
            sent_at=datetime.now()
        )
        
        # Create in-app notification
        Notification.objects.create(
            user=user,
            type='budget_warning',
            title=f'Budget Alert: {budget.category.name}',
            message=f"You've spent {budget.spent_percentage}% of your {budget.category.name} budget ({budget.currency} {budget.spent} of {budget.amount}).",
            budget_id=budget.id,
            is_email_sent=True
        )
        
        # Mark alert as sent
        budget.alert_sent = True
        budget.save(update_fields=['alert_sent'])
        
        return True
        
    except Exception as e:
        EmailLog.objects.create(
            user=user,
            subject=subject,
            recipient=user.email,
            status='failed',
            error_message=str(e)
        )
        return False


def check_all_budgets():
    """Check all budgets and send alerts if needed."""
    from apps.budgets.models import Budget
    
    active_budgets = Budget.objects.filter(is_active=True, alert_sent=False)
    
    for budget in active_budgets:
        if budget.should_alert:
            send_budget_alert(budget.user, budget)
