from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count

from .models import Category
from apps.transactions.models import Transaction


@login_required
def category_list(request):
    """List all categories for the user."""
    categories = Category.objects.filter(user=request.user).annotate(
        txn_count=Count('transactions'),
        total_amount=Sum('transactions__amount')
    ).order_by('type', 'name')
    
    income_categories = categories.filter(type='income')
    expense_categories = categories.filter(type='expense')
    
    context = {
        'income_categories': income_categories,
        'expense_categories': expense_categories,
    }
    return render(request, 'categories/list.html', context)


@login_required
def category_create(request):
    """Create a new category."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        type = request.POST.get('type', 'expense')
        icon = request.POST.get('icon', '📦')
        color = request.POST.get('color', '#4F46E5')
        description = request.POST.get('description', '')
        
        if not name:
            messages.error(request, 'Category name is required.')
            return render(request, 'categories/create.html')
        
        # Check for duplicate
        if Category.objects.filter(user=request.user, name=name, type=type).exists():
            messages.error(request, f'A {type} category with this name already exists.')
            return render(request, 'categories/create.html')
        
        Category.objects.create(
            user=request.user,
            name=name,
            type=type,
            icon=icon,
            color=color,
            description=description
        )
        messages.success(request, f'Category "{name}" created successfully!')
        return redirect('categories:list')
    
    context = {
        'icon_choices': Category.ICON_CHOICES,
    }
    return render(request, 'categories/create.html', context)


@login_required
def category_detail(request, pk):
    """View category details with transaction summary."""
    category = get_object_or_404(Category, pk=pk, user=request.user)
    
    transactions = Transaction.objects.filter(
        category=category
    ).order_by('-date')[:20]
    
    total = transactions.aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        'category': category,
        'transactions': transactions,
        'total': total,
        'transaction_count': category.transaction_count,
    }
    return render(request, 'categories/detail.html', context)


@login_required
def category_update(request, pk):
    """Update a category."""
    category = get_object_or_404(Category, pk=pk, user=request.user)
    
    if request.method == 'POST':
        category.name = request.POST.get('name', category.name).strip()
        category.icon = request.POST.get('icon', category.icon)
        category.color = request.POST.get('color', category.color)
        category.description = request.POST.get('description', '')
        category.is_active = request.POST.get('is_active') == 'on'
        
        category.save()
        messages.success(request, f'Category "{category.name}" updated!')
        return redirect('categories:list')
    
    context = {
        'category': category,
        'icon_choices': Category.ICON_CHOICES,
    }
    return render(request, 'categories/update.html', context)


@login_required
def category_delete(request, pk):
    """Delete a category (only if no transactions)."""
    category = get_object_or_404(Category, pk=pk, user=request.user)
    
    if request.method == 'POST':
        if category.transaction_count > 0:
            messages.error(
                request, 
                f'Cannot delete "{category.name}" - it has {category.transaction_count} transactions. '
                'Reassign or delete transactions first.'
            )
            return redirect('categories:detail', pk=pk)
        
        name = category.name
        category.delete()
        messages.success(request, f'Category "{name}" deleted.')
        return redirect('categories:list')
    
    context = {
        'category': category,
    }
    return render(request, 'categories/delete.html', context)
