from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.core.paginator import Paginator
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from .models import Transaction
from apps.categories.models import Category


@login_required
def transaction_list(request):
    """List transactions with filtering."""
    transactions = Transaction.objects.filter(user=request.user).select_related('category')
    
    # Filters
    category_id = request.GET.get('category')
    type_filter = request.GET.get('type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    search = request.GET.get('search', '').strip()
    
    if category_id:
        transactions = transactions.filter(category_id=category_id)
    
    if type_filter in ['income', 'expense']:
        transactions = transactions.filter(category__type=type_filter)
    
    if date_from:
        transactions = transactions.filter(date__gte=date_from)
    
    if date_to:
        transactions = transactions.filter(date__lte=date_to)
    
    if search:
        transactions = transactions.filter(description__icontains=search)
    
    transactions = transactions.order_by('-date', '-created_at')
    
    # Pagination
    paginator = Paginator(transactions, 20)
    page = request.GET.get('page', 1)
    transactions = paginator.get_page(page)
    
    # Get categories for filter dropdown
    categories = Category.objects.filter(user=request.user, is_active=True)
    
    context = {
        'transactions': transactions,
        'categories': categories,
        'filters': {
            'category': category_id,
            'type': type_filter,
            'date_from': date_from,
            'date_to': date_to,
            'search': search,
        }
    }
    return render(request, 'transactions/list.html', context)


@login_required
def transaction_create(request):
    """Create a new transaction."""
    categories = Category.objects.filter(user=request.user, is_active=True)
    expense_categories = categories.filter(type='expense')
    income_categories = categories.filter(type='income')
    
    context = {
        'expense_categories': expense_categories,
        'income_categories': income_categories,
        'currencies': ['INR', 'USD', 'EUR', 'GBP', 'AUD', 'CAD', 'JPY', 'CNY'],
        'today': date.today().isoformat(),
    }
    
    if request.method == 'POST':
        category_id = request.POST.get('category')
        amount_str = request.POST.get('amount', '0')
        currency = request.POST.get('currency', 'INR')
        trans_date = request.POST.get('date')
        description = request.POST.get('description', '')
        is_refund = request.POST.get('is_refund') == 'on'
        
        # Validate category
        try:
            category = Category.objects.get(pk=category_id, user=request.user)
        except Category.DoesNotExist:
            messages.error(request, 'Invalid category selected.')
            return render(request, 'transactions/create.html', context)
        
        # Validate and parse amount with decimal precision
        try:
            amount = Decimal(amount_str).quantize(Decimal('0.01'))
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except (InvalidOperation, ValueError) as e:
            messages.error(request, 'Please enter a valid positive amount.')
            return render(request, 'transactions/create.html', context)
        
        # Create transaction
        transaction = Transaction.objects.create(
            user=request.user,
            category=category,
            amount=amount,
            currency=currency,
            date=trans_date,
            description=description,
            is_refund=is_refund
        )
        
        # Handle receipt upload
        if 'receipt' in request.FILES:
            receipt = request.FILES['receipt']
            # Validate file size (5MB max)
            if receipt.size > 5 * 1024 * 1024:
                messages.warning(request, 'Receipt file too large (max 5MB). Transaction saved without receipt.')
            else:
                transaction.receipt = receipt
                transaction.save()
        
        messages.success(request, f'Transaction of {currency} {amount} added successfully!')
        return redirect('transactions:list')
    
    return render(request, 'transactions/create.html', context)


@login_required
def transaction_detail(request, pk):
    """View transaction details."""
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    
    context = {
        'transaction': transaction,
    }
    return render(request, 'transactions/detail.html', context)


@login_required
def transaction_update(request, pk):
    """Update a transaction."""
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    categories = Category.objects.filter(user=request.user, is_active=True)
    
    if request.method == 'POST':
        category_id = request.POST.get('category')
        amount_str = request.POST.get('amount', '0')
        
        try:
            category = Category.objects.get(pk=category_id, user=request.user)
            amount = Decimal(amount_str).quantize(Decimal('0.01'))
            if amount <= 0:
                raise ValueError()
        except (Category.DoesNotExist, InvalidOperation, ValueError):
            messages.error(request, 'Invalid category or amount.')
            return render(request, 'transactions/update.html', {
                'transaction': transaction, 'categories': categories
            })
        
        transaction.category = category
        transaction.amount = amount
        transaction.currency = request.POST.get('currency', 'INR')
        transaction.date = request.POST.get('date')
        transaction.description = request.POST.get('description', '')
        transaction.is_refund = request.POST.get('is_refund') == 'on'
        
        if 'receipt' in request.FILES:
            receipt = request.FILES['receipt']
            if receipt.size <= 5 * 1024 * 1024:
                transaction.receipt = receipt
        
        transaction.save()
        messages.success(request, 'Transaction updated!')
        return redirect('transactions:detail', pk=pk)
    
    context = {
        'transaction': transaction,
        'categories': categories,
        'currencies': ['INR', 'USD', 'EUR', 'GBP', 'AUD', 'CAD', 'JPY', 'CNY'],
    }
    return render(request, 'transactions/update.html', context)


@login_required
def transaction_delete(request, pk):
    """Delete a transaction."""
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    
    if request.method == 'POST':
        transaction.delete()
        messages.success(request, 'Transaction deleted.')
        return redirect('transactions:list')
    
    context = {
        'transaction': transaction,
    }
    return render(request, 'transactions/delete.html', context)


@login_required
def api_summary(request):
    """API endpoint for dashboard summary."""
    today = date.today()
    month_start = today.replace(day=1)
    
    transactions = Transaction.objects.filter(
        user=request.user,
        date__gte=month_start,
        date__lte=today
    )
    
    income = transactions.filter(category__type='income').aggregate(
        total=Sum('amount'))['total'] or 0
    
    expense = transactions.filter(
        category__type='expense', is_refund=False
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    return JsonResponse({
        'income': float(income),
        'expense': float(expense),
        'savings': float(income - expense),
    })


@login_required
def api_monthly_trend(request):
    """API endpoint for monthly trend chart."""
    six_months_ago = date.today() - timedelta(days=180)
    
    data = Transaction.objects.filter(
        user=request.user,
        date__gte=six_months_ago
    ).annotate(
        month=TruncMonth('date')
    ).values('month', 'category__type').annotate(
        total=Sum('amount')
    ).order_by('month')
    
    result = {}
    for item in data:
        month_key = item['month'].strftime('%Y-%m')
        if month_key not in result:
            result[month_key] = {'income': 0, 'expense': 0}
        result[month_key][item['category__type']] = float(item['total'])
    
    return JsonResponse({
        'labels': list(result.keys()),
        'income': [v['income'] for v in result.values()],
        'expense': [v['expense'] for v in result.values()],
    })
