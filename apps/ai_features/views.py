from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from django.db.models import Sum, Avg, StdDev
from django.views.decorators.http import require_POST
from decimal import Decimal
from datetime import date, timedelta
import requests
import json

from .models import AIInsight, SpendingAnomaly, ChatHistory
from apps.transactions.models import Transaction
from apps.categories.models import Category


OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


def call_deepseek(messages, max_tokens=500):
    """Call DeepSeek via OpenRouter API."""
    api_key = settings.OPENROUTER_API_KEY
    if not api_key:
        return None
    
    try:
        response = requests.post(
            OPENROUTER_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://finance-tracker.app",
            },
            json={
                "model": "deepseek/deepseek-chat",
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.7,
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"OpenRouter API error: {e}")
        return None


@login_required
def insights_list(request):
    """List AI-generated insights."""
    insights = AIInsight.objects.filter(
        user=request.user,
        is_dismissed=False
    ).order_by('-created_at')[:20]
    
    context = {
        'insights': insights,
    }
    return render(request, 'ai_features/insights.html', context)


@login_required
def generate_insights(request):
    """Generate new AI insights based on spending patterns."""
    user = request.user
    
    # Get recent transaction data
    thirty_days_ago = date.today() - timedelta(days=30)
    transactions = Transaction.objects.filter(
        user=user,
        date__gte=thirty_days_ago
    ).select_related('category')
    
    # Prepare summary for AI
    total_income = transactions.filter(category__type='income').aggregate(
        total=Sum('amount'))['total'] or Decimal('0')
    total_expense = transactions.filter(
        category__type='expense', is_refund=False
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Category breakdown
    category_spending = transactions.filter(
        category__type='expense'
    ).values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')[:5]
    
    spending_summary = ", ".join([
        f"{c['category__name']}: ₹{c['total']}" for c in category_spending
    ])
    
    # Build prompt
    prompt = f"""Analyze this user's financial data from the last 30 days and provide 3 brief, actionable insights:

Income: ₹{total_income}
Expenses: ₹{total_expense}
Savings Rate: {round((total_income - total_expense) / total_income * 100 if total_income > 0 else 0)}%
Top spending categories: {spending_summary}

Provide insights in JSON format with 'title' and 'content' for each insight. Keep each insight under 50 words. Focus on practical advice."""

    api_messages = [
        {"role": "system", "content": "You are a helpful financial advisor. Provide actionable, personalized advice based on spending data. Always respond in valid JSON format."},
        {"role": "user", "content": prompt}
    ]
    
    response = call_deepseek(api_messages, max_tokens=600)
    
    if response:
        try:
            # Try to parse JSON from response
            # Handle potential markdown code blocks
            clean_response = response.strip()
            if clean_response.startswith('```'):
                clean_response = clean_response.split('```')[1]
                if clean_response.startswith('json'):
                    clean_response = clean_response[4:]
            
            insights_data = json.loads(clean_response)
            
            # Handle if it's a list directly or nested
            if isinstance(insights_data, dict) and 'insights' in insights_data:
                insights_data = insights_data['insights']
            
            for insight in insights_data[:3]:
                AIInsight.objects.create(
                    user=user,
                    type='spending_analysis',
                    title=insight.get('title', 'Financial Insight'),
                    content=insight.get('content', '')
                )
            
            messages.success(request, 'New insights generated!')
        except (json.JSONDecodeError, KeyError) as e:
            # If JSON parsing fails, create single insight from raw text
            AIInsight.objects.create(
                user=user,
                type='spending_analysis',
                title='Financial Analysis',
                content=response[:500]
            )
            messages.success(request, 'Insight generated!')
    else:
        messages.error(request, 'Could not generate insights. Please check API settings.')
    
    return redirect('ai_features:insights')


@login_required
def dismiss_insight(request, pk):
    """Dismiss an insight."""
    insight = get_object_or_404(AIInsight, pk=pk, user=request.user)
    insight.is_dismissed = True
    insight.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('ai_features:insights')


@login_required
def chat_assistant(request):
    """Chat with AI financial assistant."""
    chat_history = ChatHistory.objects.filter(user=request.user).order_by('-created_at')[:50]
    chat_history = reversed(list(chat_history))  # Show oldest first
    
    # Calculate monthly context
    today = date.today()
    month_start = today.replace(day=1)
    
    monthly_income = Transaction.objects.filter(
        user=request.user,
        date__gte=month_start,
        date__lte=today,
        category__type='income'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    monthly_expenses = Transaction.objects.filter(
        user=request.user,
        date__gte=month_start,
        date__lte=today,
        category__type='expense',
        is_refund=False
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    net_savings = monthly_income - monthly_expenses
    
    context = {
        'chat_history': chat_history,
        'monthly_income': monthly_income,
        'monthly_expenses': monthly_expenses,
        'net_savings': net_savings,
    }
    return render(request, 'ai_features/chat.html', context)


@login_required
@require_POST
def chat_send(request):
    """Send a message to AI assistant."""
    user_message = request.POST.get('message', '').strip()
    
    if not user_message:
        return JsonResponse({'error': 'Message is required'}, status=400)
    
    # Save user message
    ChatHistory.objects.create(
        user=request.user,
        role='user',
        content=user_message
    )
    
    # Get recent chat history for context
    recent_history = ChatHistory.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]
    
    # Get financial context
    thirty_days_ago = date.today() - timedelta(days=30)
    recent_spending = Transaction.objects.filter(
        user=request.user,
        category__type='expense',
        date__gte=thirty_days_ago
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    recent_income = Transaction.objects.filter(
        user=request.user,
        category__type='income',
        date__gte=thirty_days_ago
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Build messages for API
    api_messages = [
        {
            "role": "system", 
            "content": f"""You are a helpful financial assistant for a personal finance tracker app. 
The user's financial context (last 30 days):
- Total Income: ₹{recent_income}
- Total Expenses: ₹{recent_spending}
- Savings: ₹{recent_income - recent_spending}

Be concise, helpful, and provide actionable advice. Keep responses under 150 words."""
        }
    ]
    
    # Add recent conversation history
    for msg in reversed(list(recent_history)[:6]):
        api_messages.append({"role": msg.role, "content": msg.content})
    
    api_messages.append({"role": "user", "content": user_message})
    
    # Get AI response
    response = call_deepseek(api_messages, max_tokens=300)
    
    if response:
        # Save assistant response
        ChatHistory.objects.create(
            user=request.user,
            role='assistant',
            content=response
        )
        return JsonResponse({'response': response})
    else:
        return JsonResponse({
            'response': "I'm sorry, I couldn't process your request. Please try again later."
        })


@login_required
@require_POST
def chat_clear(request):
    """Clear chat history."""
    ChatHistory.objects.filter(user=request.user).delete()
    messages.success(request, 'Chat history cleared.')
    return redirect('ai_features:chat')


@login_required
def anomaly_list(request):
    """List detected spending anomalies."""
    anomalies = SpendingAnomaly.objects.filter(
        user=request.user,
        is_reviewed=False
    ).select_related('transaction', 'transaction__category').order_by('-created_at')[:30]
    
    context = {
        'anomalies': anomalies,
    }
    return render(request, 'ai_features/anomalies.html', context)


@login_required
def anomaly_review(request, pk):
    """Review and mark an anomaly."""
    anomaly = get_object_or_404(SpendingAnomaly, pk=pk, user=request.user)
    
    if request.method == 'POST':
        is_false_positive = request.POST.get('false_positive') == 'true'
        anomaly.is_reviewed = True
        anomaly.is_false_positive = is_false_positive
        anomaly.save()
        messages.success(request, 'Anomaly reviewed.')
        return redirect('ai_features:anomalies')
    
    context = {
        'anomaly': anomaly,
    }
    return render(request, 'ai_features/anomaly_review.html', context)


def detect_anomalies_for_user(user):
    """Detect spending anomalies for a user."""
    # Get last 90 days of transactions
    ninety_days_ago = date.today() - timedelta(days=90)
    
    transactions = Transaction.objects.filter(
        user=user,
        category__type='expense',
        date__gte=ninety_days_ago,
        is_refund=False
    ).select_related('category')
    
    if transactions.count() < 10:
        return []  # Not enough data
    
    anomalies_created = []
    
    # Calculate statistics per category
    category_stats = transactions.values('category').annotate(
        avg_amount=Avg('amount'),
        std_amount=StdDev('amount')
    )
    
    stats_dict = {s['category']: s for s in category_stats}
    
    # Check recent transactions for anomalies
    recent = transactions.filter(date__gte=date.today() - timedelta(days=7))
    
    for t in recent:
        stats = stats_dict.get(t.category_id)
        if not stats or not stats['std_amount']:
            continue
        
        avg = Decimal(str(stats['avg_amount']))
        std = Decimal(str(stats['std_amount']))
        
        # Check if amount is > 2 standard deviations from mean
        if std > 0 and t.amount > avg + (2 * std):
            deviation = ((t.amount - avg) / avg * 100) if avg > 0 else 0
            
            # Don't create duplicate anomalies
            if not SpendingAnomaly.objects.filter(transaction=t).exists():
                anomaly = SpendingAnomaly.objects.create(
                    user=user,
                    transaction=t,
                    type='unusual_amount',
                    severity='high' if deviation > 200 else 'medium',
                    description=f"This {t.category.name} expense of ₹{t.amount} is {deviation:.0f}% higher than your average of ₹{avg:.0f}.",
                    expected_amount=avg,
                    deviation_percentage=deviation
                )
                anomalies_created.append(anomaly)
    
    return anomalies_created


@login_required
@require_POST
def auto_categorize(request):
    """Auto-categorize a transaction description using AI."""
    description = request.POST.get('description', '').strip()
    
    if not description:
        return JsonResponse({'error': 'Description required'}, status=400)
    
    # Get user's categories
    categories = Category.objects.filter(user=request.user, is_active=True)
    category_names = [f"{c.name} ({c.type})" for c in categories]
    
    prompt = f"""Given this transaction description: "{description}"

Which of these categories is the best match? Categories: {', '.join(category_names)}

Respond with just the category name, nothing else."""

    api_messages = [
        {"role": "system", "content": "You are a transaction categorization assistant. Respond only with the category name."},
        {"role": "user", "content": prompt}
    ]
    
    response = call_deepseek(api_messages, max_tokens=50)
    
    if response:
        # Find matching category
        suggested_name = response.strip().split('(')[0].strip()
        matching = categories.filter(name__iexact=suggested_name).first()
        
        if matching:
            return JsonResponse({
                'category_id': matching.id,
                'category_name': matching.name,
                'category_type': matching.type
            })
    
    return JsonResponse({'category_id': None, 'message': 'Could not suggest category'})
