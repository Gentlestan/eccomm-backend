# payments/services/paystack.py

import hmac
import hashlib
import requests
from django.conf import settings

# Paystack secret key from Django settings
PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY


def verify_paystack_payment(reference: str) -> dict:
    """
    Verify a Paystack payment server-side using the transaction reference.
    Returns the Paystack response JSON.
    Raises requests.HTTPError on request failure.
    """
    url = f"https://api.paystack.co/transaction/verify/{reference}"

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()  # Raise exception if HTTP error
    return response.json()


def verify_webhook_signature(request_body: bytes, signature: str) -> bool:
    """
    Verify Paystack webhook signature.

    Paystack sends a header 'x-paystack-signature' which must match
    HMAC-SHA512 of the request body using the secret key.

    Returns True if valid, False otherwise.
    """
    if not signature:
        return False

    computed_hmac = hmac.new(
        key=PAYSTACK_SECRET_KEY.encode("utf-8"),
        msg=request_body,
        digestmod=hashlib.sha512
    ).hexdigest()

    return hmac.compare_digest(computed_hmac, signature)
