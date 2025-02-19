from django.db import models

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

    date = models.DateTimeField()  # Takes user input
    description = models.CharField(max_length=255)
    amount = models.IntegerField()
    category = models.CharField(max_length=50, default='Other')
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    mode_of_transaction = models.CharField(max_length=20, choices=MODE_CHOICES)

    def __str__(self):
        return f"{self.description} - {self.transaction_type} - ₹{self.amount}"
