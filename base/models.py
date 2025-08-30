from django.db import models
from django.contrib.auth.models import AbstractUser
from decimal import Decimal

class CustomUser(AbstractUser):
    ROLE_CHOICES=[
                ('admin','admin'),
                ('roommate','roommate'),
    ]
    full_name = models.CharField(max_length=21, blank=True, null=True) 
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='roommate')
    is_approved = models.BooleanField(default=False) 
    room_capacity = models.PositiveIntegerField(default=0, null=True, blank=True)  
    room_name = models.CharField(max_length=100, null=True, blank=True)
    room = models.ForeignKey("Room", on_delete=models.SET_NULL, null=True, blank=True)

    assigned_admin = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="roommates"
    )

    def is_admin(self):
        return self.role == 'admin'
    
    def is_roommate(self):
        return self.role == 'roommate'
    

class Transaction(models.Model):
    
    TYPE_CHOICES = [
        ('Income', 'Income'),
        ('Expense', 'Expense'),
    ]

    MODE_CHOICES = [
        ('Cash', 'Cash'),
        ('Bank transfer', 'Bank Transfer'),
        ('PhonePe', 'PhonePe'),
        ('Gpay', 'Gpay'),
        ('Paytm', 'Paytm'),
    ]
    roommate = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="roommate_transactions", null=True, blank=True)
    rent_plan = models.ForeignKey("RentPlan",on_delete=models.CASCADE,null=True, blank=True)
    admin = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="transactions")
    date = models.DateTimeField()  # Takes user input
    description = models.CharField(max_length=255)
    amount = models.IntegerField()
    category = models.CharField(max_length=50, default='Other')
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    mode_of_transaction = models.CharField(max_length=20, choices=MODE_CHOICES)

    def __str__(self):
        return f"{self.description} - {self.transaction_type} - ₹{self.amount}"



class Room(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="admin_room")
    room_name = models.CharField(max_length=100)
    capacity = models.IntegerField(default=1) 
    
    @property
    def available_vacancies(self):
        return self.capacity - CustomUser.objects.filter(room=self, role="roommate", is_approved=True).count()

    def __str__(self):
        return f"{self.room_name} ({self.available_vacancies} vacancies left)"
    



class RentPlan(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="rent_plan")
    start_date = models.DateField(null=True, blank=True) 
    monthly_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.admin.username} - ₹{self.monthly_amount}"

class Payment(models.Model):
    MODE_CHOICES = [
        ('Cash', 'Cash'),
        ('PhonePe', 'PhonePe'),
        ('GPay', 'GPay'),
        ('Paytm', 'Paytm'),
        ('Bank Transfer', 'Bank Transfer'),
    ]

    roommate = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="payments")
    rent_plan = models.ForeignKey(RentPlan, on_delete=models.CASCADE, related_name="payments")
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    mode_of_transaction = models.CharField(max_length=20, choices=MODE_CHOICES, default="Cash")
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.roommate.full_name} - ₹{self.amount_paid} ({self.mode_of_transaction})"
