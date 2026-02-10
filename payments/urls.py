# payments/urls.py

from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from .views import PaystackVerifyView, PaystackWebhookView

urlpatterns = [
    # Endpoint for verifying payments from frontend (requires authentication)
    path("paystack/verify/", PaystackVerifyView.as_view(), name="paystack-verify"),

    # Endpoint for Paystack webhook (CSRF exempted)
    path(
        "paystack/webhook/",
        csrf_exempt(PaystackWebhookView.as_view()),
        name="paystack-webhook",
    ),
]
