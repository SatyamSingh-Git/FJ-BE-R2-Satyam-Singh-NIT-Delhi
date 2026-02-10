from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import date
from decimal import Decimal, InvalidOperation

from .models import Budget
from apps.categories.models import Category


@login_required
def budget_list(request):
    """List all budgets with progress."""
    budgets = Budget.objects.filter(
        user=request.user
    ).select_related('category').order_by('-is_active', '-created_at')
    
    # Separate active and inactive
    active_budgets = [b for b in budgets if b.is_active]
    inactive_budgets = [b for b in budgets if not b.is_active]
    
    context = {
        'active_budgets': active_budgets,
        'inactive_budgets': inactive_budgets,
    }
    return render(request, 'budgets/list.html', context)


@login_required
def budget_create(request):
    """Create a new budget."""
    # Only expense categories make sense for budgeting
    categories = Category.objects.filter(
        user=request.user, 
        type='expense', 
        is_active=True
    )
    
    if request.method == 'POST':
        category_id = request.POST.get('category')
        amount_str = request.POST.get('amount', '0')
        period = request.POST.get('period', 'monthly')
        start_date = request.POST.get('start_date')
        alert_threshold = request.POST.get('alert_threshold', '80')
        
        try:
            category = Category.objects.get(pk=category_id, user=request.user)
            amount = Decimal(amount_str).quantize(Decimal('0.01'))
            alert_pct = int(alert_threshold)
        except (Category.DoesNotExist, InvalidOperation, ValueError):
            messages.error(request, 'Invalid category or amount.')
            return render(request, 'budgets/create.html', {'categories': categories})
        
        # Check for existing active budget for same category
        if Budget.objects.filter(
            user=request.user, 
            category=category, 
            is_active=True
        ).exists():
            messages.error(request, f'An active budget already exists for {category.name}.')
            return render(request, 'budgets/create.html', {'categories': categories})
        
        Budget.objects.create(
            user=request.user,
            category=category,
            amount=amount,
            period=period,
            start_date=start_date or date.today(),
            alert_at_percentage=alert_pct
        )
        
        messages.success(request, f'Budget for {category.name} created!')
        return redirect('budgets:list')
    
    context = {
        'categories': categories,
        'today': date.today().isoformat(),
    }
    return render(request, 'budgets/create.html', context)


@login_required
def budget_detail(request, pk):
    """View budget details with spending breakdown."""
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    
    # Get transactions in this budget period
    from apps.transactions.models import Transaction
    end_date = budget.end_date or date.today()
    transactions = Transaction.objects.filter(
        user=request.user,
        category=budget.category,
        date__gte=budget.start_date,
        date__lte=end_date
    ).order_by('-date')[:20]
    
    context = {
        'budget': budget,
        'transactions': transactions,
        'status': budget.get_status(),
    }
    return render(request, 'budgets/detail.html', context)


@login_required
def budget_update(request, pk):
    """Update a budget."""
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    
    if request.method == 'POST':
        try:
            budget.amount = Decimal(request.POST.get('amount', '0')).quantize(Decimal('0.01'))
            budget.alert_at_percentage = int(request.POST.get('alert_threshold', '80'))
            budget.is_active = request.POST.get('is_active') == 'on'
            budget.end_date = request.POST.get('end_date') or None
            budget.save()
            messages.success(request, 'Budget updated!')
            return redirect('budgets:detail', pk=pk)
        except (InvalidOperation, ValueError):
            messages.error(request, 'Invalid amount.')
    
    context = {
        'budget': budget,
    }
    return render(request, 'budgets/update.html', context)


@login_required
def budget_delete(request, pk):
    """Delete a budget."""
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    
    if request.method == 'POST':
        budget.delete()
        messages.success(request, 'Budget deleted.')
        return redirect('budgets:list')
    
    context = {
        'budget': budget,
    }
    return render(request, 'budgets/delete.html', context)
