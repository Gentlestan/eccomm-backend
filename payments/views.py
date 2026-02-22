# payments/views.py

from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from orders.models import Order, OrderItem
from gadjet_shop.models import Product
from payments.models import Payment
from payments.serializers import PaystackVerifySerializer
from payments.services.paystack import verify_paystack_payment, verify_webhook_signature


class PaystackVerifyView(APIView):
    """
    Webhook-first approach:
    - Frontend only sends 'reference' and optionally 'pending_order_id'.
    - Backend verifies payment, checks server-side order/cart.
    - Ensures no trusting frontend items or totals.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaystackVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reference = serializer.validated_data["reference"]
        pending_order_id = serializer.validated_data.get("pending_order_id")

        # Prevent duplicate verified payments
        if Payment.objects.filter(reference=reference, status="verified").exists():
            return Response(
                {"detail": "Payment already verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify with Paystack API
        try:
            paystack_response = verify_paystack_payment(reference)
        except Exception as e:
            return Response(
                {"detail": f"Error verifying payment: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if not paystack_response.get("status"):
            return Response(
                {"detail": "Payment verification failed from Paystack."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = paystack_response["data"]
        if data.get("status") != "success":
            return Response(
                {"detail": "Payment was not successful."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Convert amount to Decimal for safe money comparison
        amount_paid = Decimal(data.get("amount", 0)) / Decimal("100")

        # Fetch pending order or cart from backend
        try:
            order = Order.objects.select_for_update().get(id=pending_order_id, user=request.user, status="pending")
        except Order.DoesNotExist:
            return Response(
                {"detail": "Pending order not found or already processed."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Calculate order total server-side
        order_total = sum(
            Decimal(item.product.price) * item.quantity for item in order.items.all()
        )

        # Validate payment amount matches server-side order total
        if order_total != amount_paid:
            return Response(
                {
                    "detail": "Payment amount does not match order total.",
                    "order_total": order_total,
                    "amount_paid": amount_paid,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # At this point: verification passed, proceed with stock deduction & payment recording
        with transaction.atomic():
            # Lock all products for this order
            product_ids = [item.product.id for item in order.items.all()]
            products_map = {
                p.id: p for p in Product.objects.select_for_update().filter(id__in=product_ids)
            }

            # Check stock again in case concurrent orders reduced stock
            out_of_stock_items = []
            for item in order.items.all():
                product = products_map[item.product.id]
                if product.stock < item.quantity:
                    out_of_stock_items.append({
                        "product_id": product.id,
                        "product_name": product.name,
                        "available_stock": product.stock,
                        "requested_quantity": item.quantity,
                    })

            if out_of_stock_items:
                return Response(
                    {
                        "detail": "Some products are out of stock.",
                        "out_of_stock": out_of_stock_items,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Deduct stock
            for item in order.items.all():
                product = products_map[item.product.id]
                product.stock -= item.quantity
                product.save(update_fields=["stock"])

            # Record verified payment
            Payment.objects.create(
                user=request.user,
                order=order,
                reference=reference,
                amount=amount_paid,
                status="verified",
                provider_response=data,
                verified_at=timezone.now(),
            )

            # Finalize order
            order.status = "processing"
            order.processing_at = timezone.now()
            order.total_price = order_total
            order.save(update_fields=["status", "processing_at", "total_price"])

        return Response(
            {
                "detail": "Payment verified and order processed successfully.",
                "order_id": order.id,
                "total_price": order_total,
            },
            status=status.HTTP_201_CREATED,
        )


class PaystackWebhookView(APIView):
    """
    Handles Paystack webhook events asynchronously.
    - Verifies signature
    - Ensures idempotency
    - Updates order & payment securely
    """
    permission_classes = []  # Public webhook

    def post(self, request):
        signature = request.headers.get("x-paystack-signature")
        if not verify_webhook_signature(request.body, signature):
            return Response({"detail": "Invalid webhook signature."}, status=status.HTTP_400_BAD_REQUEST)

        event = request.data
        event_type = event.get("event")
        data = event.get("data", {})

        reference = data.get("reference")
        amount_paid = Decimal(data.get("amount", 0)) / Decimal("100")

        if event_type != "charge.success":
            return Response({"detail": "Event ignored."}, status=status.HTTP_200_OK)

        # Avoid duplicate processing
        if Payment.objects.filter(reference=reference, status="verified").exists():
            return Response({"detail": "Payment already verified."}, status=status.HTTP_200_OK)

        with transaction.atomic():
            try:
                payment = Payment.objects.select_related("order").get(reference=reference)
            except Payment.DoesNotExist:
                return Response({"detail": "Payment record not found."}, status=status.HTTP_404_NOT_FOUND)

            # Update payment and order
            payment.status = "verified"
            payment.verified_at = timezone.now()
            payment.amount = amount_paid
            payment.save(update_fields=["status", "verified_at", "amount"])

            order = payment.order
            order.status = "processing"
            order.processing_at = timezone.now()
            order.save(update_fields=["status", "processing_at"])

        return Response({"detail": "Webhook processed successfully."}, status=status.HTTP_200_OK)
