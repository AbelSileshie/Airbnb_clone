from django.db import models
from django.contrib.auth.models import User
from Apps.Properties.models import Booking

class PaymentMethod(models.Model):
    METHOD_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('paypal', 'PayPal'),
        ('stripe', 'Stripe'),
    ]
    name = models.CharField(max_length=50, choices=METHOD_CHOICES, unique=True)
    details = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.get_name_display()

class Payment(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payment_app_payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, default='completed')

    def __str__(self):
        return f"Payment {self.id} for Booking {self.booking_id}"
