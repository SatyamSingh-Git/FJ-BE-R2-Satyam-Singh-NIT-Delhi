from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum
from django.db.models.functions import TruncMonth, TruncWeek, TruncDate
from datetime import date, timedelta
from decimal import Decimal
import csv
import io
import json

from apps.transactions.models import Transaction
from apps.categories.models import Category


@login_required
def reports_home(request):
    """Reports overview page."""
    return render(request, 'reports/home.html')


@login_required
def chart_data(request):
    """API endpoint for chart data - returns JSON."""
    period = request.GET.get('period', 'daily')
    today = date.today()
    
    if period == 'daily':
        # Last 30 days
        start_date = today - timedelta(days=29)
        transactions = Transaction.objects.filter(
            user=request.user,
            date__gte=start_date,
            date__lte=today
        ).values('date', 'category__type', 'is_refund').annotate(
            total=Sum('amount')
        ).order_by('date')
        
        # Build daily data
        data = {}
        current = start_date
        while current <= today:
            data[current.isoformat()] = {'income': 0, 'expense': 0}
            current += timedelta(days=1)
        
        for t in transactions:
            key = t['date'].isoformat()
            if t['category__type'] == 'income':
                data[key]['income'] += float(t['total'])
            elif t['category__type'] == 'expense' and not t['is_refund']:
                data[key]['expense'] += float(t['total'])
        
        labels = list(data.keys())
        income = [data[k]['income'] for k in labels]
        expense = [data[k]['expense'] for k in labels]
        # Format labels for display
        labels = [date.fromisoformat(l).strftime('%d %b') for l in labels]
        
    elif period == 'weekly':
        # Last 12 weeks
        start_date = today - timedelta(weeks=12)
        transactions = Transaction.objects.filter(
            user=request.user,
            date__gte=start_date,
            date__lte=today
        ).annotate(
            week=TruncWeek('date')
        ).values('week', 'category__type', 'is_refund').annotate(
            total=Sum('amount')
        ).order_by('week')
        
        # Build weekly data
        data = {}
        current = start_date
        while current <= today:
            week_start = current - timedelta(days=current.weekday())
            week_key = week_start.isoformat()
            if week_key not in data:
                data[week_key] = {'income': 0, 'expense': 0}
            current += timedelta(weeks=1)
        
        for t in transactions:
            if t['week']:
                key = t['week'].isoformat()
                if key in data:
                    if t['category__type'] == 'income':
                        data[key]['income'] += float(t['total'])
                    elif t['category__type'] == 'expense' and not t['is_refund']:
                        data[key]['expense'] += float(t['total'])
        
        sorted_keys = sorted(data.keys())
        labels = [date.fromisoformat(k).strftime('Week of %d %b') for k in sorted_keys]
        income = [data[k]['income'] for k in sorted_keys]
        expense = [data[k]['expense'] for k in sorted_keys]
        
    else:  # monthly
        # Last 12 months
        start_date = date(today.year - 1, today.month, 1)
        transactions = Transaction.objects.filter(
            user=request.user,
            date__gte=start_date,
            date__lte=today
        ).annotate(
            month=TruncMonth('date')
        ).values('month', 'category__type', 'is_refund').annotate(
            total=Sum('amount')
        ).order_by('month')
        
        # Build monthly data
        data = {}
        current = start_date
        while current <= today:
            month_key = current.strftime('%Y-%m')
            if month_key not in data:
                data[month_key] = {'income': 0, 'expense': 0}
            if current.month == 12:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)
        
        for t in transactions:
            if t['month']:
                key = t['month'].strftime('%Y-%m')
                if key in data:
                    if t['category__type'] == 'income':
                        data[key]['income'] += float(t['total'])
                    elif t['category__type'] == 'expense' and not t['is_refund']:
                        data[key]['expense'] += float(t['total'])
        
        sorted_keys = sorted(data.keys())[-12:]  # Last 12 months
        labels = [date(int(k[:4]), int(k[5:]), 1).strftime('%b %Y') for k in sorted_keys]
        income = [data[k]['income'] for k in sorted_keys]
        expense = [data[k]['expense'] for k in sorted_keys]
    
    return JsonResponse({
        'labels': labels,
        'income': income,
        'expense': expense
    })


@login_required
@login_required
def monthly_report(request):
    """Monthly income vs expenses report with category breakdown."""
    import calendar
    from django.db.models import Sum, Q, F

    # Get parameters
    today = date.today()
    current_month = int(request.GET.get('month', today.month))
    current_year = int(request.GET.get('year', today.year))
    
    # Calculate date range for current month
    _, last_day = calendar.monthrange(current_year, current_month)
    start_date = date(current_year, current_month, 1)
    end_date = date(current_year, current_month, last_day)
    
    # Calculate previous month for comparison
    prev_date = start_date - timedelta(days=1)
    prev_month_start = date(prev_date.year, prev_date.month, 1)
    prev_month_end = prev_date
    
    # 1. Overall Stats
    total_income = Transaction.objects.filter(
        user=request.user,
        date__gte=start_date,
        date__lte=end_date,
        category__type='income'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    total_expenses = Transaction.objects.filter(
        user=request.user,
        date__gte=start_date,
        date__lte=end_date,
        category__type='expense',
        is_refund=False
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Previous month expenses for comparison
    prev_expenses = Transaction.objects.filter(
        user=request.user,
        date__gte=prev_month_start,
        date__lte=prev_month_end,
        category__type='expense',
        is_refund=False
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    income_count = Transaction.objects.filter(
        user=request.user,
        date__gte=start_date,
        date__lte=end_date,
        category__type='income'
    ).count()

    net_savings = total_income - total_expenses
    savings_rate = (net_savings / total_income * 100) if total_income > 0 else 0
    
    expense_change = 0
    if prev_expenses > 0:
        expense_change = ((total_expenses - prev_expenses) / prev_expenses) * 100
        
    expense_percent = 0
    if total_income > 0:
        expense_percent = (total_expenses / total_income) * 100
    
    # 2. Category Breakdown
    from apps.budgets.models import Budget
    
    categories = Category.objects.filter(user=request.user, type='expense')
    category_breakdown = []
    
    current_day = min(today.day, last_day) if (current_month == today.month and current_year == today.year) else last_day
    days_in_month = last_day
    
    for cat in categories:
        spent = Transaction.objects.filter(
            user=request.user,
            category=cat,
            date__gte=start_date,
            date__lte=end_date,
            is_refund=False
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Get monthly budget for this category
        budget = Budget.objects.filter(
            user=request.user, 
            category=cat, 
            period='monthly',
            is_active=True
        ).first()
        
        budget_amount = budget.amount if budget else Decimal('0')
        
        if spent > 0 or budget_amount > 0:
            variance = budget_amount - spent
            variance_percent = 0
            if budget_amount > 0:
                variance_percent = ((budget_amount - spent) / budget_amount) * 100
            elif spent > 0:
                variance_percent = -100 # Totally over budget
            
            category_breakdown.append({
                'name': cat.name,
                'icon': cat.icon,
                'spent': spent,
                'budget': budget_amount,
                'variance': variance,
                'variance_percent': variance_percent
            })
    
    # Sort by spent desc
    category_breakdown.sort(key=lambda x: x['spent'], reverse=True)
    
    # 3. Quick Analysis
    highest_variance = None # Most Overspent
    best_category = None    # Most Saved
    
    overspent_cats = [c for c in category_breakdown if c['variance'] < 0]
    underspent_cats = [c for c in category_breakdown if c['variance'] > 0 and c['budget'] > 0]
    
    if overspent_cats:
        highest_variance = min(overspent_cats, key=lambda x: x['variance']) # Most negative variance
        
    if underspent_cats:
        best_category = max(underspent_cats, key=lambda x: x['variance'])   # Most positive variance

    # Projected savings (simple linear projection)
    projected_savings = net_savings
    if current_month == today.month and current_year == today.year and current_day > 0:
         daily_avg_spend = total_expenses / current_day
         projected_expense = daily_avg_spend * days_in_month
         projected_savings = total_income - projected_expense


    # Context for dropdowns
    month_list = [{'value': i, 'name': calendar.month_name[i]} for i in range(1, 13)]
    year_list = range(today.year, today.year - 5, -1)

    context = {
        'current_month': current_month,
        'current_year': current_year,
        'month_name': calendar.month_name[current_month],
        'months': month_list,
        'years': year_list,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'income_count': income_count,
        'net_savings': net_savings,
        'savings_rate': savings_rate,
        'expense_change': expense_change,
        'expense_percent': expense_percent,
        'category_breakdown': category_breakdown,
        'highest_variance': highest_variance,
        'best_category': best_category,
        'projected_savings': projected_savings
    }
    return render(request, 'reports/monthly.html', context)


# Import models for the filter
from django.db import models


@login_required
def category_report(request):
    """Category-wise spending report."""
    # Date range
    period = request.GET.get('period', 'month')
    today = date.today()
    
    if period == 'week':
        start_date = today - timedelta(days=7)
    elif period == 'month':
        start_date = today.replace(day=1)
    elif period == 'year':
        start_date = today.replace(month=1, day=1)
    else:
        start_date = today - timedelta(days=30)
    
    # Category aggregation
    expense_data = Transaction.objects.filter(
        user=request.user,
        date__gte=start_date,
        date__lte=today,
        category__type='expense',
        is_refund=False
    ).values(
        'category__name', 'category__color', 'category__icon'
    ).annotate(
        total=Sum('amount'),
        count=models.Count('id')
    ).order_by('-total')
    
    income_data = Transaction.objects.filter(
        user=request.user,
        date__gte=start_date,
        date__lte=today,
        category__type='income'
    ).values(
        'category__name', 'category__color', 'category__icon'
    ).annotate(
        total=Sum('amount'),
        count=models.Count('id')
    ).order_by('-total')
    
    total_expense = sum(item['total'] for item in expense_data)
    total_income = sum(item['total'] for item in income_data)
    
    context = {
        'expense_data': expense_data,
        'income_data': income_data,
        'total_expense': total_expense,
        'total_income': total_income,
        'period': period,
        'start_date': start_date,
        'end_date': today,
    }
    return render(request, 'reports/category.html', context)


@login_required
def export_csv(request):
    """Export transactions as CSV."""
    # Get date range
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    transactions = Transaction.objects.filter(
        user=request.user
    ).select_related('category').order_by('-date')
    
    if date_from:
        transactions = transactions.filter(date__gte=date_from)
    if date_to:
        transactions = transactions.filter(date__lte=date_to)
    
    # Create CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="transactions_{date.today()}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'Category', 'Type', 'Amount', 'Currency', 'Description', 'Is Refund'])
    
    for t in transactions:
        writer.writerow([
            t.date.isoformat(),
            t.category.name,
            t.category.type,
            str(t.amount),
            t.currency,
            t.description,
            'Yes' if t.is_refund else 'No'
        ])
    
    return response


@login_required
def export_pdf(request):
    """Export transactions as PDF (simple HTML-to-PDF approach)."""
    # For a production app, use reportlab or weasyprint
    # This returns a simple HTML response that can be printed to PDF
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    transactions = Transaction.objects.filter(
        user=request.user
    ).select_related('category').order_by('-date')
    
    if date_from:
        transactions = transactions.filter(date__gte=date_from)
    if date_to:
        transactions = transactions.filter(date__lte=date_to)
    
    # Calculate totals
    total_income = transactions.filter(category__type='income').aggregate(
        total=Sum('amount'))['total'] or 0
    total_expense = transactions.filter(
        category__type='expense', is_refund=False
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        'transactions': transactions[:100],  # Limit for PDF
        'total_income': total_income,
        'total_expense': total_expense,
        'net_savings': total_income - total_expense,
        'date_from': date_from or 'All time',
        'date_to': date_to or date.today(),
        'export_date': date.today(),
    }
    return render(request, 'reports/export_pdf.html', context)
