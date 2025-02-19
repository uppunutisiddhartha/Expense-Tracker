from datetime import datetime
from django.shortcuts import render, redirect
from .models import Transaction

def index(request):
   
    
    if request.method == 'POST':
        date_str = request.POST.get('date')  
        formatted_date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M")  
        
        Transaction.objects.create(
            date=formatted_date,
            description=request.POST.get('description'),
            amount=int(request.POST.get('amount')),  
            category=request.POST.get('category'),
            transaction_type=request.POST.get('transaction_type'),
            mode_of_transaction=request.POST.get('mode_of_transaction'),
        )
        return redirect('/') 
    
   
    transactions = Transaction.objects.all()

    total_income = sum(t.amount for t in transactions if t.transaction_type == "Income")
    total_expense = sum(t.amount for t in transactions if t.transaction_type == "Expense")

   
    net_worth = total_income - total_expense
    savings = net_worth 

    return render(request, 'index.html', {
        'transactions': transactions,
        'total_income': total_income,
        'total_expense': total_expense,
        'net_worth': net_worth,
        'savings': savings
    })
