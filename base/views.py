from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.db import models
from django.conf import settings
from django.views.decorators.cache import never_cache
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.core.exceptions import MultipleObjectsReturned
import random
import string
from decimal import Decimal
from datetime import datetime, timedelta


from .models import CustomUser, Room, Transaction, Payment, RentPlan

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
        full_name = request.POST.get("full_name")
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        admin_email = request.POST.get("admin_email")

        # Check if admin exists
        try:
            admin_user = CustomUser.objects.get(email=admin_email, role="admin")
        except CustomUser.DoesNotExist:
            messages.error(request, "Admin not found.")
            return redirect("roommate_register")

        # Create/get admin's room
        room, created = Room.objects.get_or_create(
            admin=admin_user,
            defaults={"room_name": f"{admin_user.username}'s Room", "capacity": 5}
        )

        # Check capacity (only approved roommates count)
        if room.available_vacancies <= 0:
            messages.error(request, "No vacancies available in this room.")
            return redirect("roommate_register")

        # Prevent duplicate usernames/emails
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect("roommate_register")
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect("roommate_register")

        # Create roommate (pending approval)
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

        # Notify admin
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
        action = request.POST.get("action")

        # ---------------- Normal Login ----------------
        if action == "password_login":
            username = request.POST["username"]
            password = request.POST["password"]
            user = authenticate(request, username=username, password=password)

            if user is not None:
                if user.is_roommate() and not user.is_approved:
                    messages.error(request, "Your account is pending admin approval.")
                    return redirect("login")

                login(request, user)
                return redirect("index" if user.is_admin() else "userpage")

            else:
                messages.error(request, "Invalid credentials.")
                return redirect("login")

        # ---------------- Send OTP ----------------
        elif action == "send_otp":
            email = request.POST.get("email")
            users = CustomUser.objects.filter(email=email)

            if not users.exists():
                messages.error(request, "Email not registered.")
                return redirect("login")

            if users.count() > 1:
                messages.error(request, "Multiple accounts found with this email. Please use username login.")
                return redirect("login")

            user = users.first()

            # ✅ Clear old OTP data before generating a new one
            for key in ["otp", "otp_email", "otp_expiry", "otp_attempts"]:
                request.session.pop(key, None)

            otp = ''.join(random.choices(string.digits, k=6))
            request.session['otp'] = otp
            request.session['otp_email'] = email
            request.session['otp_expiry'] = (timezone.now() + timedelta(minutes=5)).isoformat()
            request.session['otp_attempts'] = 0
            request.session.modified = True
            print("NEW OTP GENERATED:", otp, "FOR:", email)
            print("SESSION AFTER SET:", dict(request.session))


            # Send OTP email
            send_mail(
                "Your Login OTP",
                f"Your OTP is {otp}. It expires in 5 minutes.",
                settings.DEFAULT_FROM_EMAIL,
                [email],
            )

            messages.success(request, "OTP sent to your email.")
            return redirect("verify_otp")

    return render(request, "login.html")


def verify_otp(request):
    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        saved_otp = request.session.get("otp")
        email = request.session.get("otp_email")
        expiry = request.session.get("otp_expiry")

        if not (saved_otp and email and expiry):
            messages.error(request, "Session expired. Try again.")
            return redirect("login")

        # Convert expiry string to datetime
        expiry_dt = parse_datetime(expiry)
        if not expiry_dt:
            messages.error(request, "Invalid OTP expiry. Try again.")
            return redirect("login")

        # Check if OTP has expired
        if timezone.now() > expiry_dt:
            messages.error(request, "OTP expired. Please login again.")
            # clear otp-related data
            for key in ["otp", "otp_email", "otp_expiry"]:
                request.session.pop(key, None)
            return redirect("login")

        if entered_otp == saved_otp:
            try:
                user = CustomUser.objects.get(email=email)

                # Block roommates if not approved
                if user.is_roommate() and not user.is_approved:
                    messages.error(request, "Your account is pending admin approval.")
                    return redirect("login")

                login(request, user)

                # ✅ Clear OTP-related session data after successful login
                for key in ["otp", "otp_email", "otp_expiry"]:
                    request.session.pop(key, None)

                messages.success(request, "Login successful!")
                return redirect("index" if user.is_admin() else "userpage")

            except CustomUser.DoesNotExist:
                messages.error(request, "User not found.")
                return redirect("login")

            except CustomUser.MultipleObjectsReturned:
                messages.error(request, "Multiple accounts found with this email. Please use username login.")
                return redirect("login")

        else:
            messages.error(request, "Invalid OTP. Try again.")
            return redirect("verify_otp")

    return render(request, "verify_otp.html")

def custom_logout(request):
    logout(request)
    return redirect("login")


# ---------------- TRANSACTIONS ----------------

@login_required
@never_cache

def index(request):
    if request.user.is_roommate() and not request.user.is_approved:
        messages.error(request, "Your account is not approved yet.")
        return redirect("login")

    roommates = (
        CustomUser.objects.filter(assigned_admin=request.user, role="roommate", is_approved=True)
        if request.user.is_admin()
        else []
    )

    admins = CustomUser.objects.filter(role="admin") if request.user.is_admin() else []

    # Handle Add Transaction
    if request.method == "POST" and request.user.is_admin():
        date_str = request.POST.get("date")
        try:
            formatted_date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M")
        except (ValueError, TypeError):
            messages.error(request, "Invalid date format.")
            return redirect("index")

        selected_id = request.POST.get("roommate")
        roommate = None
        if selected_id and not selected_id.startswith("admin-"):
            try:
                roommate = CustomUser.objects.get(id=selected_id)
            except CustomUser.DoesNotExist:
                messages.error(request, "Selected roommate does not exist.")
                return redirect("index")

        Transaction.objects.create(
            admin=request.user,
            roommate=roommate,
            date=formatted_date,
            description=request.POST.get("description"),
            amount=Decimal(request.POST.get("amount") or 0),
            category=request.POST.get("category"),
            transaction_type=request.POST.get("transaction_type"),
            mode_of_transaction=request.POST.get("mode_of_transaction"),
        )
        return redirect("index")

    transactions = Transaction.objects.all().order_by("-date")
    total_income = sum(t.amount for t in transactions if t.transaction_type == "Income")
    total_expense = sum(t.amount for t in transactions if t.transaction_type == "Expense")
    adjusted_expense = max(total_expense - total_income, Decimal(0))

    rent_plan = RentPlan.objects.filter(admin=request.user).first()
    expected_rent = rent_plan.monthly_amount * (roommates.count() + 1) if rent_plan else Decimal(0)  # include admin

    rent_collected = Payment.objects.filter(rent_plan__admin=request.user).aggregate(
        total=models.Sum("amount_paid")
    )["total"] or Decimal(0)

    draft = expected_rent - rent_collected
    savings = max(rent_collected - adjusted_expense, Decimal(0))

    return render(request, "index.html", {
        "transactions": transactions,
        "roommates": roommates,
        "admins": admins,
        "total_income": total_income,
        "total_expense": adjusted_expense,
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

    # --- Roommates & Payment Data ---
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

    total_expected= rent_plan.monthly_amount * (roommates.count() + 1) if rent_plan else Decimal(0)

    draft = total_expected - total_collected

    # --- Transactions ---
    # Fetch transactions related to the admin OR this user (if roommate)
    transactions = Transaction.objects.filter(
        admin=admin_user
    ).order_by('-date')

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
        return redirect("login")

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
    all_users = list(roommates) + [admin_user]  # Include admin for payments

    roommate_data = []
    total_collected = Decimal(0)

    for user in all_users:
        payments = Payment.objects.filter(roommate=user, rent_plan=rent_plan)
        total_paid = sum(p.amount_paid for p in payments)
        balance = rent_plan.monthly_amount - total_paid
        total_collected += total_paid

        roommate_data.append({
            "roommate": user,
            "total_paid": total_paid,
            "balance": balance,
            "payments": payments
        })

    total_expected = rent_plan.monthly_amount * Decimal(len(all_users))  # includes admin
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
        "admin_user_id": admin_user.id,
    })

# def verify_otp(request):
#     if request.method == "POST":
#         entered_otp = request.POST.get("otp")
#         saved_otp = request.session.get("otp")
#         email = request.session.get("otp_email")
#         expiry = request.session.get("otp_expiry")

#         if not (saved_otp and email and expiry):
#             messages.error(request, "Session expired. Try again.")
#             return redirect("login")

#         # ✅ fixed here
#         if timezone.now() > datetime.fromisoformat(expiry):
#             messages.error(request, "OTP expired. Please login again.")
#             return redirect("login")

#         if entered_otp == saved_otp:
#             try:
#                 user = CustomUser.objects.get(email=email)
#                 login(request, user)
#                 messages.success(request, "Login successful!")
#                 return redirect("index" if user.is_admin() else "userpage")
#             except CustomUser.DoesNotExist:
#                 messages.error(request, "User not found.")
#                 return redirect("login")
#         else:
#             messages.error(request, "Invalid OTP.")
#             return redirect("verify_otp")

#     return render(request, "verify_otp.html")
def about(request):
    return render(request, "about.html")