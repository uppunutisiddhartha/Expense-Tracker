from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .models import *
from datetime import datetime
from decimal import Decimal


# ---------------- AUTH ----------------

def admin_register(request):
    if request.method == "POST":
        full_name = request.POST["full_name"]
        username = request.POST["username"]
        email = request.POST["email"]
        password = request.POST["password"]
        room_name = request.POST["room_name"]
        capacity = request.POST["capacity"]

        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return render(request, "admin_register.html")

        # create admin user
        admin_user = CustomUser.objects.create_user(
            full_name=full_name,
            username=username,
            email=email,
            password=password,
            role="admin",
            is_approved=True,
        )

        # create room
        Room.objects.create(
            admin=admin_user,
            room_name=room_name,
            capacity=int(capacity),
        )

        messages.success(request, "Admin registered successfully. Please login.")
        return redirect("login")

    return render(request, "admin_register.html")


def roommate_register(request):
    if request.method == "POST":
        full_name = request.POST["full_name"]
        username = request.POST["username"]
        email = request.POST["email"]
        password = request.POST["password"]
        admin_email = request.POST["admin_email"]

        try:
            admin_user = CustomUser.objects.get(email=admin_email, role="admin")
        except CustomUser.DoesNotExist:
            messages.error(request, "Admin not found.")
            return redirect("roommate_register")

        # ensure admin has a room
        room, created = Room.objects.get_or_create(
            admin=admin_user,
            defaults={"room_name": f"{admin_user.username}'s Room", "capacity": 5}
        )

        # check capacity
        if room.available_vacancies <= 0:
            messages.error(request, "No vacancies available in this room.")
            return redirect("roommate_register")

        # ✅ fixed typo (full_name)
        roommate = CustomUser.objects.create_user(
            full_name=full_name,
            username=username,
            email=email,
            password=password,
            role="roommate",
            assigned_admin=admin_user,
            room=room,
            is_approved=False
        )

        # notify admin
        send_mail(
            "New Roommate Request",
            f"{roommate.username} ({roommate.email}) has requested to join {room.room_name}.",
            settings.DEFAULT_FROM_EMAIL,
            [admin_user.email],
        )

        messages.success(request, "Registered successfully! Waiting for admin approval.")
        return redirect("login")

    return render(request, "roommate_register.html")


def custom_login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_roommate() and not user.is_approved:
                messages.error(request, "Your account is pending admin approval.")
                return redirect("login")

            login(request, user)

            if user.is_admin():
                return redirect("index")
            else:
                return redirect("userpage")
        else:
            messages.error(request, "Invalid credentials.")
            return redirect("login")

    return render(request, "login.html")


def custom_logout(request):
    logout(request)
    return redirect("login")


# ---------------- TRANSACTIONS ----------------

from decimal import Decimal
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from .models import CustomUser, Transaction, Payment, RentPlan


@login_required
def index(request):
    if request.user.is_roommate() and not request.user.is_approved:
        messages.error(request, "Your account is not approved yet.")
        return redirect("login")

    # Admin can see roommates
    roommates = CustomUser.objects.filter(
        assigned_admin=request.user, role="roommate", is_approved=True
    ) if request.user.is_admin() else []

    # ----------------- Handle Add Transaction -----------------
    if request.method == "POST" and request.user.is_admin():
        date_str = request.POST.get("date")
        formatted_date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M")
        roommate_id = request.POST.get("roommate")
        roommate = CustomUser.objects.get(id=roommate_id) if roommate_id else None

        Transaction.objects.create(
            admin=request.user,
            roommate=roommate,
            date=formatted_date,
            description=request.POST.get("description"),
            amount=Decimal(request.POST.get("amount")),
            category=request.POST.get("category"),
            transaction_type=request.POST.get("transaction_type"),
            mode_of_transaction=request.POST.get("mode_of_transaction"),
        )
        return redirect("index")

    # ----------------- Dashboard Calculations -----------------
    transactions = Transaction.objects.all().order_by("-date")

    # Separate incomes and expenses from Transaction
    total_income = sum(t.amount for t in transactions if t.transaction_type == "Income")
    total_expense = sum(t.amount for t in transactions if t.transaction_type == "Expense")

    # Rent Plan (to calculate expected rent & savings)
    rent_plan = RentPlan.objects.filter(admin=request.user).first()

    if rent_plan:
        expected_rent = rent_plan.monthly_amount * CustomUser.objects.filter(
            assigned_admin=request.user, role="roommate", is_approved=True
        ).count()
    else:
        expected_rent = Decimal(0)

    # Rent Collected (from Payments)
    rent_collected = Payment.objects.filter(rent_plan__admin=request.user).aggregate(
        total=models.Sum("amount_paid")
    )["total"] or Decimal(0)

    # Draft = Expected rent - collected rent
    draft = expected_rent - rent_collected

    # Savings = Rent collected + income - expenses
    savings = rent_collected + total_income - total_expense

    return render(request, "index.html", {
        "transactions": transactions,
        "roommates": roommates,
        "total_income": total_income,
        "total_expense": total_expense,
        "expected_rent": expected_rent,
        "rent_collected": rent_collected,
        "draft": draft,
        "savings": savings,
    })

@login_required
def approve_roommates(request):
    if not request.user.is_authenticated or not request.user.is_admin():
        messages.error(request, "Only admins can access this page.")
        return redirect("login")

    pending_users = CustomUser.objects.filter(
        assigned_admin=request.user,
        role="roommate",
        is_approved=False
    )

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        action = request.POST.get("action")
        roommate = CustomUser.objects.get(id=user_id)

        if action == "approve":
            roommate.is_approved = True
            roommate.save()
            send_mail(
                "Roommate Request Approved",
                f"Hello {roommate.username}, your request to join {roommate.room.room_name} has been approved!",
                settings.DEFAULT_FROM_EMAIL,
                [roommate.email],
            )
        elif action == "reject":
            send_mail(
                "Roommate Request Rejected",
                f"Hello {roommate.username}, your request to join {roommate.room.room_name} was rejected.",
                settings.DEFAULT_FROM_EMAIL,
                [roommate.email],
            )
            roommate.delete()

        return redirect("approve_roommates")

    return render(request, "approve_roommates.html", {"pending_users": pending_users})



# ---------------- USER PAGE ----------------
@login_required
def userpage(request):
    user = request.user

    # Get the admin assigned to this user
    admin_user = user.assigned_admin
    if not admin_user:
        messages.error(request, "No admin assigned to you yet.")
        return redirect("login")

    # Get or create the rent plan of the admin
    rent_plan, _ = RentPlan.objects.get_or_create(admin=admin_user)

    # --- Dashboard Data ---
    roommates = CustomUser.objects.filter(assigned_admin=admin_user, role="roommate")
    roommate_count = roommates.count()

    roommate_data = []
    total_collected = Decimal(0)

    for rm in roommates:
        payments = Payment.objects.filter(roommate=rm, rent_plan=rent_plan)
        total_paid = sum(p.amount_paid for p in payments)
        balance = rent_plan.monthly_amount - total_paid
        total_collected += total_paid

        roommate_data.append({
            "roommate": rm,
            "total_paid": total_paid,
            "balance": balance,
            "payments": payments
        })

    total_expected = rent_plan.monthly_amount * Decimal(roommate_count)
    draft = total_expected - total_collected

    transactions = Transaction.objects.filter(rent_plan=rent_plan).order_by('-date')
    total_expenses = sum(t.amount for t in transactions if t.transaction_type == "Expense")
    total_income = sum(t.amount for t in transactions if t.transaction_type == "Income")
    savings = total_collected - total_expenses + total_income

    return render(request, "userpage.html", {
        "transactions": transactions,
        "roommates": roommates,
        "total_expected": total_expected,
        "rent_collected": total_collected,
        "draft": draft,
        "total_expense": total_expenses,
        "total_income": total_income,
        "savings": savings,
    })



# ---------------- RENT DASHBOARD ----------------

@login_required
def admin_rent_dashboard(request):
    admin_user = request.user
    if not admin_user.is_admin():
        return redirect("rent_status")

    rent_plan, created = RentPlan.objects.get_or_create(admin=admin_user)

    # --- Update rent plan ---
    if "update_rent_plan" in request.POST:
        rent_plan.start_date = request.POST.get("start_date")
        rent_plan.monthly_amount = Decimal(request.POST.get("monthly_amount"))
        rent_plan.save()
        return redirect("admin_rent_dashboard")

    # --- Record payment ---
    if "record_payment" in request.POST:
        roommate_id = request.POST.get("roommate")
        amount = Decimal(request.POST.get("amount"))
        mode = request.POST.get("mode_of_transaction")

        roommate = CustomUser.objects.get(id=roommate_id)

        Payment.objects.create(
            roommate=roommate,
            rent_plan=rent_plan,
            amount_paid=amount,
            mode_of_transaction=mode
        )

        return redirect("admin_rent_dashboard")

    # --- Record expense ---
    if "record_expense" in request.POST:
        description = request.POST.get("description")
        amount = Decimal(request.POST.get("amount"))
        Transaction.objects.create(
            rent_plan=rent_plan,
            transaction_type="Expense",
            amount=amount,
            description=description
        )
        return redirect("admin_rent_dashboard")

    # --- Record income ---
    if "record_income" in request.POST:
        description = request.POST.get("description")
        amount = Decimal(request.POST.get("amount"))
        Transaction.objects.create(
            rent_plan=rent_plan,
            transaction_type="Income",
            amount=amount,
            description=description
        )
        return redirect("admin_rent_dashboard")

    # --- Dashboard Data ---
    roommates = CustomUser.objects.filter(assigned_admin=admin_user, role="roommate")
    roommate_count = roommates.count()

    roommate_data = []
    total_collected = Decimal(0)

    for rm in roommates:
        payments = Payment.objects.filter(roommate=rm, rent_plan=rent_plan)
        total_paid = sum(p.amount_paid for p in payments)
        balance = rent_plan.monthly_amount - total_paid
        total_collected += total_paid

        roommate_data.append({
            "roommate": rm,
            "total_paid": total_paid,
            "balance": balance,
            "payments": payments
        })

    total_expected = rent_plan.monthly_amount * Decimal(roommate_count)
    draft = total_expected - total_collected

    transactions = Transaction.objects.filter(rent_plan=rent_plan)
    total_expenses = sum(t.amount for t in transactions if t.transaction_type == "Expense")
    total_income = sum(t.amount for t in transactions if t.transaction_type == "Income")

    savings = total_collected - total_expenses + total_income

    return render(request, "admin_rent_dashboard.html", {
        "rent_plan": rent_plan,
        "roommates": roommate_data,
        "total_expected": total_expected,
        "total_collected": total_collected,
        "draft": draft,
        "total_expenses": total_expenses,
        "total_income": total_income,
        "savings": savings,
    })
