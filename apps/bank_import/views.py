from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from datetime import datetime
from decimal import Decimal, InvalidOperation
import csv
import io

from .models import BankStatementImport, ImportedTransaction, CategorizationRule
from apps.transactions.models import Transaction
from apps.categories.models import Category


@login_required
def import_list(request):
    """List all bank imports."""
    imports = BankStatementImport.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'imports': imports,
    }
    return render(request, 'bank_import/list.html', context)


@login_required
def upload_statement(request):
    """Upload a bank statement."""
    if request.method == 'POST':
        file = request.FILES.get('file')
        
        if not file:
            messages.error(request, 'Please select a file.')
            return render(request, 'bank_import/upload.html')
        
        filename = file.name.lower()
        if filename.endswith('.csv'):
            file_type = 'csv'
        elif filename.endswith('.pdf'):
            file_type = 'pdf'
        else:
            messages.error(request, 'Only CSV and PDF files are supported.')
            return render(request, 'bank_import/upload.html')
        
        # Create import record
        import_record = BankStatementImport.objects.create(
            user=request.user,
            file=file,
            file_type=file_type,
            file_name=file.name,
            status='pending'
        )
        
        messages.success(request, f'File "{file.name}" uploaded. Click Process to parse transactions.')
        return redirect('bank_import:detail', pk=import_record.pk)
    
    return render(request, 'bank_import/upload.html')


@login_required
def import_detail(request, pk):
    """View import details and parsed transactions."""
    import_record = get_object_or_404(BankStatementImport, pk=pk, user=request.user)
    
    parsed_transactions = ImportedTransaction.objects.filter(
        import_batch=import_record
    ).order_by('-date')
    
    # Get categories for assignment
    categories = Category.objects.filter(user=request.user, is_active=True)
    
    context = {
        'statement': import_record,
        'transactions': parsed_transactions,
        'categories': categories,
    }
    return render(request, 'bank_import/detail.html', context)


def parse_csv_statement(file_content, user):
    """Parse CSV bank statement."""
    transactions = []
    
    # Try to detect CSV format
    reader = csv.DictReader(io.StringIO(file_content))
    
    for row in reader:
        # Try common column name patterns
        date_val = row.get('Date') or row.get('date') or row.get('Transaction Date') or row.get('Txn Date')
        desc_val = row.get('Description') or row.get('description') or row.get('Particulars') or row.get('Narration')
        
        # Amount handling - some have separate debit/credit columns
        amount_val = row.get('Amount') or row.get('amount')
        debit_val = row.get('Debit') or row.get('debit') or row.get('Withdrawal')
        credit_val = row.get('Credit') or row.get('credit') or row.get('Deposit')
        
        if not date_val or not desc_val:
            continue
        
        try:
            # Parse date - try common formats
            for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%d %b %Y']:
                try:
                    parsed_date = datetime.strptime(date_val.strip(), fmt).date()
                    break
                except ValueError:
                    continue
            else:
                continue  # Skip if no format matches
            
            # Parse amount
            if amount_val:
                amount_str = amount_val.replace(',', '').replace('₹', '').replace('$', '').strip()
                amount = abs(Decimal(amount_str))
                trans_type = 'debit' if amount_str.startswith('-') or float(amount_str) < 0 else 'credit'
            elif debit_val and debit_val.strip():
                amount = abs(Decimal(debit_val.replace(',', '').strip()))
                trans_type = 'debit'
            elif credit_val and credit_val.strip():
                amount = abs(Decimal(credit_val.replace(',', '').strip()))
                trans_type = 'credit'
            else:
                continue
            
            transactions.append({
                'date': parsed_date,
                'description': desc_val.strip(),
                'amount': amount,
                'transaction_type': trans_type,
                'reference': row.get('Reference') or row.get('Ref No') or ''
            })
            
        except (ValueError, InvalidOperation):
            continue
    
    return transactions


def parse_pdf_statement(file_path):
    """Parse PDF bank statement using pdfplumber."""
    transactions = []
    
    try:
        import pdfplumber
        
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table[1:]:  # Skip header row
                        if len(row) >= 3:
                            try:
                                # Attempt to parse - format varies by bank
                                date_str = row[0] if row[0] else ''
                                desc = row[1] if len(row) > 1 else ''
                                amount_str = row[-1] if row[-1] else ''
                                
                                if not date_str or not desc:
                                    continue
                                
                                # Try to parse date
                                parsed_date = None
                                for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d %b %Y']:
                                    try:
                                        parsed_date = datetime.strptime(date_str.strip(), fmt).date()
                                        break
                                    except (ValueError, TypeError):
                                        continue
                                
                                if not parsed_date:
                                    continue
                                
                                # Parse amount
                                amount_str = str(amount_str).replace(',', '').replace('₹', '').strip()
                                if not amount_str:
                                    continue
                                    
                                amount = abs(Decimal(amount_str))
                                trans_type = 'debit' if '-' in str(row[-1]) else 'credit'
                                
                                transactions.append({
                                    'date': parsed_date,
                                    'description': desc.strip(),
                                    'amount': amount,
                                    'transaction_type': trans_type,
                                    'reference': ''
                                })
                            except (ValueError, InvalidOperation, TypeError):
                                continue
    except Exception as e:
        print(f"PDF parsing error: {e}")
    
    return transactions


def auto_categorize_transaction(description, user):
    """Auto-categorize based on rules and keywords."""
    description_lower = description.lower()
    
    # Check user's custom rules first
    rules = CategorizationRule.objects.filter(user=user, is_active=True)
    for rule in rules:
        keyword_lower = rule.keyword.lower()
        matched = False
        
        if rule.match_type == 'exact' and description_lower == keyword_lower:
            matched = True
        elif rule.match_type == 'starts' and description_lower.startswith(keyword_lower):
            matched = True
        elif rule.match_type == 'contains' and keyword_lower in description_lower:
            matched = True
        
        if matched:
            rule.match_count += 1
            rule.save(update_fields=['match_count'])
            return rule.category, Decimal('0.95')  # High confidence for rule match
    
    # Default keyword mapping
    keyword_mapping = {
        'salary': 'Salary',
        'grocery': 'Food & Dining',
        'restaurant': 'Food & Dining',
        'uber': 'Transport',
        'ola': 'Transport',
        'petrol': 'Transport',
        'amazon': 'Shopping',
        'flipkart': 'Shopping',
        'netflix': 'Subscriptions',
        'spotify': 'Subscriptions',
        'electricity': 'Bills & Utilities',
        'mobile recharge': 'Bills & Utilities',
        'hospital': 'Health',
        'pharmacy': 'Health',
        'zomato': 'Food & Dining',
        'swiggy': 'Food & Dining',
    }
    
    for keyword, category_name in keyword_mapping.items():
        if keyword in description_lower:
            category = Category.objects.filter(
                user=user, 
                name__iexact=category_name,
                is_active=True
            ).first()
            if category:
                return category, Decimal('0.7')
    
    # Fallback to 'Other' category if no match
    cat_type = 'expense' # Default to expense if unknown, but better if we passed type
    # We don't have transaction type here easily without changing signature
    # So let's return None here and handle the default assignment in import_detail where we have the transaction
    
    return None, Decimal('0')


def check_duplicate(date, amount, description, user):
    """Check if this transaction might be a duplicate."""
    # Check for exact match within 3 days
    from datetime import timedelta
    
    potential_duplicates = Transaction.objects.filter(
        user=user,
        amount=amount,
        date__range=(date - timedelta(days=3), date + timedelta(days=3))
    )
    
    for t in potential_duplicates:
        # Simple similarity check
        if t.description.lower() == description.lower():
            return True
        # Check if descriptions are similar (simple approach)
        if len(set(t.description.lower().split()) & set(description.lower().split())) >= 2:
            return True
    
    return False


@login_required
def process_import(request, pk):
    """Process uploaded statement and parse transactions."""
    import_record = get_object_or_404(BankStatementImport, pk=pk, user=request.user)
    
    if import_record.status != 'pending':
        messages.warning(request, 'This import has already been processed.')
        return redirect('bank_import:detail', pk=pk)
    
    import_record.status = 'processing'
    import_record.save()
    
    try:
        if import_record.file_type == 'csv':
            file_content = import_record.file.read().decode('utf-8')
            parsed = parse_csv_statement(file_content, request.user)
        else:
            parsed = parse_pdf_statement(import_record.file.path)
        
        import_record.total_transactions = len(parsed)
        
        # Create ImportedTransaction records
        for t in parsed:
            is_dup = check_duplicate(t['date'], t['amount'], t['description'], request.user)
            category, confidence = auto_categorize_transaction(t['description'], request.user)
            
            # Use default 'Other' category if no auto-categorization
            if not category:
                cat_type = 'expense' if t['transaction_type'] == 'debit' else 'income'
                cat_name = 'Other Expenses' if cat_type == 'expense' else 'Other Income'
                
                category = Category.objects.filter(
                    user=request.user, 
                    name=cat_name, 
                    type=cat_type
                ).first()
                
                if not category:
                    # Create if doesn't exist
                    category = Category.objects.create(
                        user=request.user,
                        name=cat_name,
                        type=cat_type,
                        icon='📦' if cat_type == 'expense' else '💰',
                        color='#6B7280'
                    )
                confidence = Decimal('0.5')

            ImportedTransaction.objects.create(
                import_batch=import_record,
                date=t['date'],
                description=t['description'],
                amount=t['amount'],
                transaction_type=t['transaction_type'],
                suggested_category=category,
                confidence_score=confidence,
                external_reference=t.get('reference', ''),
                status='duplicate' if is_dup else 'pending'
            )
            
            if is_dup:
                import_record.duplicate_count += 1
        
        import_record.status = 'completed'
        import_record.processed_at = datetime.now()
        import_record.save()
        
        messages.success(request, f'Parsed {len(parsed)} transactions. {import_record.duplicate_count} potential duplicates found.')
        
    except Exception as e:
        import_record.status = 'failed'
        import_record.error_message = str(e)
        import_record.save()
        messages.error(request, f'Error processing file: {e}')
    
    return redirect('bank_import:detail', pk=pk)


@login_required
def approve_transactions(request, pk):
    """Approve and create actual transactions from imports."""
    import_record = get_object_or_404(BankStatementImport, pk=pk, user=request.user)
    
    if request.method != 'POST':
        return redirect('bank_import:detail', pk=pk)
    
    # Get selected transaction IDs and their categories
    approved_count = 0
    
    for key, value in request.POST.items():
        if key.startswith('category_'):
            trans_id = key.replace('category_', '')
            try:
                imported = ImportedTransaction.objects.get(
                    pk=trans_id,
                    import_batch=import_record,
                    status__in=['pending', 'duplicate']
                )
                
                if value:
                    category = Category.objects.get(pk=value, user=request.user)
                else:
                    # Fallback for uncategorized
                    cat_type = 'expense' if imported.transaction_type == 'debit' else 'income'
                    cat_name = 'Other Expenses' if cat_type == 'expense' else 'Other Income'
                    
                    category = Category.objects.filter(
                        user=request.user, 
                        name=cat_name, 
                        type=cat_type
                    ).first()
                    
                    if not category:
                        # Create if doesn't exist
                        category = Category.objects.create(
                            user=request.user,
                            name=cat_name,
                            type=cat_type,
                            icon='📦' if cat_type == 'expense' else '💰',
                            color='#6B7280'
                        )
                
                # Determine if it's income or expense based on category type
                # and transaction type (credit/debit)
                is_refund = False
                if imported.transaction_type == 'credit' and category.type == 'expense':
                    is_refund = True
                
                # Create the actual transaction
                transaction = Transaction.objects.create(
                    user=request.user,
                    category=category,
                    amount=imported.amount,
                    date=imported.date,
                    description=imported.description,
                    is_imported=True,
                    is_refund=is_refund,
                    external_id=imported.external_reference
                )
                
                imported.status = 'approved'
                imported.created_transaction = transaction
                imported.save()
                
                approved_count += 1
                
            except (ImportedTransaction.DoesNotExist, Category.DoesNotExist, ValueError):
                continue
    
    import_record.imported_count = approved_count
    import_record.save()
    
    if approved_count > 0:
        messages.success(request, f'Created {approved_count} transactions from import.')
    else:
        messages.warning(request, 'Created 0 transactions. Please ensure you select a category for each transaction you want to import.')
        
    return redirect('bank_import:detail', pk=pk)


@login_required
def categorization_rules(request):
    """View and manage categorization rules."""
    rules = CategorizationRule.objects.filter(user=request.user).order_by('-match_count')
    
    context = {
        'rules': rules,
    }
    return render(request, 'bank_import/rules.html', context)


@login_required
def create_rule(request):
    """Create a new categorization rule."""
    categories = Category.objects.filter(user=request.user, is_active=True)
    
    if request.method == 'POST':
        keyword = request.POST.get('keyword', '').strip()
        match_type = request.POST.get('match_type', 'contains')
        category_id = request.POST.get('category')
        
        if not keyword:
            messages.error(request, 'Keyword is required.')
            return render(request, 'bank_import/create_rule.html', {'categories': categories})
        
        try:
            category = Category.objects.get(pk=category_id, user=request.user)
        except Category.DoesNotExist:
            messages.error(request, 'Invalid category.')
            return render(request, 'bank_import/create_rule.html', {'categories': categories})
        
        CategorizationRule.objects.create(
            user=request.user,
            keyword=keyword,
            match_type=match_type,
            category=category
        )
        
        messages.success(request, f'Rule created: "{keyword}" → {category.name}')
        return redirect('bank_import:rules')
    
    context = {
        'categories': categories,
    }
    return render(request, 'bank_import/create_rule.html', context)


@login_required
def delete_rule(request, pk):
    """Delete a categorization rule."""
    rule = get_object_or_404(CategorizationRule, pk=pk, user=request.user)
    
    if request.method == 'POST':
        rule.delete()
        messages.success(request, 'Rule deleted.')
        return redirect('bank_import:rules')
    
    return render(request, 'bank_import/delete_rule.html', {'rule': rule})
