from django.db import models
from django.conf import settings
from orders.models import Order

class Payment(models.Model):
    STATUS_CHOICES = [
        ("initialized", "Initialized"),
        ("verified", "Verified"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="payment"
    )

    reference = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=5, default="NGN")

    provider = models.CharField(max_length=20, default="paystack")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="initialized"
    )

    provider_response = models.JSONField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.reference} - {self.status}"
