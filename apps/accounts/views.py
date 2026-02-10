from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from datetime import date, timedelta
from decimal import Decimal

from .models import UserProfile
from apps.transactions.models import Transaction
from apps.categories.models import Category
from apps.budgets.models import Budget
from apps.notifications.models import Notification


def home(request):
    """Landing page."""
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    return render(request, 'home.html')


@login_required
def dashboard(request):
    """Main dashboard with financial overview."""
    user = request.user
    today = date.today()
    
    # Current month date range
    month_start = today.replace(day=1)
    month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    # Get transactions for current month
    month_transactions = Transaction.objects.filter(
        user=user,
        date__gte=month_start,
        date__lte=month_end
    )
    
    # Calculate totals
    income_total = month_transactions.filter(
        category__type='income'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    expense_total = month_transactions.filter(
        category__type='expense',
        is_refund=False
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    refunds_total = month_transactions.filter(
        is_refund=True
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    savings = income_total - expense_total + refunds_total
    
    # YTD Transactions for Top Categories
    year_start = today.replace(month=1, day=1)
    
    # Calculate YTD totals for percentage calculation base
    income_total_ytd = Transaction.objects.filter(
        user=user,
        date__gte=year_start,
        date__lte=today,
        category__type='income'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    expense_total_ytd = Transaction.objects.filter(
        user=user,
        date__gte=year_start,
        date__lte=today,
        category__type='expense',
        is_refund=False
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    # Category breakdown for charts (YTD)
    expense_cats = Transaction.objects.filter(
        user=user,
        date__gte=year_start,
        date__lte=today,
        category__type='expense',
        is_refund=False
    ).values('category__name', 'category__color', 'category__icon').annotate(
        total=Sum('amount')
    ).order_by('-total')[:3]
    
    expense_by_category = []
    if expense_total_ytd > 0:
        for cat in expense_cats:
            percent = (cat['total'] / expense_total_ytd) * 100
            expense_by_category.append({
                'name': cat['category__name'],
                'color': cat['category__color'],
                'icon': cat['category__icon'],
                'total': cat['total'],
                'percent': percent
            })
    
    income_cats = Transaction.objects.filter(
        user=user,
        date__gte=year_start,
        date__lte=today,
        category__type='income'
    ).values('category__name', 'category__color', 'category__icon').annotate(
        total=Sum('amount')
    ).order_by('-total')[:3]

    income_by_category = []
    if income_total_ytd > 0:
        for cat in income_cats:
            percent = (cat['total'] / income_total_ytd) * 100
            income_by_category.append({
                'name': cat['category__name'],
                'color': cat['category__color'],
                'icon': cat['category__icon'],
                'total': cat['total'],
                'percent': percent
            })
    
    # Last 6 months trend
    six_months_ago = today - timedelta(days=180)
    monthly_trend = Transaction.objects.filter(
        user=user,
        date__gte=six_months_ago
    ).annotate(
        month=TruncMonth('date')
    ).values('month', 'category__type').annotate(
        total=Sum('amount')
    ).order_by('month')
    
    # Process monthly trend data for chart
    trend_data = {}
    for item in monthly_trend:
        month_key = item['month'].strftime('%b %Y')
        if month_key not in trend_data:
            trend_data[month_key] = {'income': 0, 'expense': 0}
        trend_data[month_key][item['category__type']] = float(item['total'])
    
    # Recent transactions
    recent_transactions = Transaction.objects.filter(
        user=user
    ).select_related('category').order_by('-date', '-created_at')[:10]
    
    # Active budgets with status (sort in Python since spent_percentage is a property)
    active_budgets = list(Budget.objects.filter(
        user=user,
        is_active=True,
        start_date__lte=today
    ).select_related('category'))
    active_budgets.sort(key=lambda b: b.spent_percentage, reverse=True)
    active_budgets = active_budgets[:5]
    
    budget_alerts = [b for b in active_budgets if b.spent_percentage >= 80]
    
    # Unread notifications
    unread_notifications = Notification.objects.filter(
        user=user,
        is_read=False
    ).order_by('-created_at')[:5]
    
    context = {
        'income_total': income_total,
        'expense_total': expense_total,
        'refunds_total': refunds_total,
        'savings': savings,
        'expense_by_category': list(expense_by_category),
        'income_by_category': list(income_by_category),
        'trend_labels': list(trend_data.keys()),
        'trend_income': [v['income'] for v in trend_data.values()],
        'trend_expense': [v['expense'] for v in trend_data.values()],
        'recent_transactions': recent_transactions,
        'active_budgets': active_budgets,
        'budget_alerts': budget_alerts,
        'unread_notifications': unread_notifications,
        'current_month': today.strftime('%B %Y'),
    }
    
    return render(request, 'dashboard.html', context)


@login_required
def profile(request):
    """View user profile."""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    # Create default categories if new user
    if created:
        Category.create_default_categories(request.user)
    
    context = {
        'profile': profile,
        'transaction_count': Transaction.objects.filter(user=request.user).count(),
        'category_count': Category.objects.filter(user=request.user).count(),
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_update(request):
    """Update user profile."""
    profile = request.user.profile
    
    if request.method == 'POST':
        # Update user fields
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.save()
        
        # Update profile fields
        profile.phone = request.POST.get('phone', '')
        profile.preferred_currency = request.POST.get('preferred_currency', 'INR')
        profile.email_notifications = request.POST.get('email_notifications') == 'on'
        profile.budget_alert_threshold = int(request.POST.get('budget_alert_threshold', 80))
        
        # Handle avatar upload
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']
        
        profile.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('accounts:profile')
    
    return render(request, 'accounts/profile_update.html', {'profile': profile})
