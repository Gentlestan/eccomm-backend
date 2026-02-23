# payments/views.py

import uuid
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
    Verify Paystack payment using pending order UUID (public_id),
    validate stock, create order items & payment, deduct inventory.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaystackVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reference = serializer.validated_data["reference"]
        pending_order_id = serializer.validated_data["pending_order_id"]
        shipping_address = serializer.validated_data.get("shipping_address", "")

        # 1️⃣ Convert string to UUID
        try:
            pending_order_uuid = uuid.UUID(pending_order_id)
        except ValueError:
            return Response({"detail": "Invalid pending_order_id."}, status=400)

        # 2️⃣ Fetch pending order using public_id
        try:
            order = Order.objects.get(
                public_id=pending_order_uuid,
                user=request.user,
                status="pending"
            )
        except Order.DoesNotExist:
            return Response({"detail": "Pending order not found."}, status=status.HTTP_404_NOT_FOUND)

        # 3️⃣ Prevent duplicate verified payments
        if Payment.objects.filter(reference=reference, status="verified").exists():
            return Response({"detail": "Payment already verified."}, status=status.HTTP_400_BAD_REQUEST)

        # 4️⃣ Verify payment with Paystack API
        try:
            paystack_response = verify_paystack_payment(reference)
        except Exception as e:
            return Response({"detail": f"Error verifying payment: {str(e)}"}, status=status.HTTP_502_BAD_GATEWAY)

        if not paystack_response.get("status") or paystack_response["data"].get("status") != "success":
            return Response({"detail": "Payment was not successful."}, status=status.HTTP_400_BAD_REQUEST)

        amount_paid = paystack_response["data"]["amount"] / 100  # Convert kobo → naira

        # 5️⃣ Process order atomically
        with transaction.atomic():
            order_total = 0
            out_of_stock_items = []

            # Lock product rows
            product_ids = [item.product.id for item in order.items.all()]
            products_map = {
                p.id: p for p in Product.objects.select_for_update().filter(id__in=product_ids)
            }

            # Validate stock
            for item in order.items.all():
                product = products_map.get(item.product.id)
                if not product:
                    out_of_stock_items.append({
                        "product_id": item.product.id,
                        "available_stock": 0,
                        "requested_quantity": item.quantity
                    })
                    continue
                if product.stock < item.quantity:
                    out_of_stock_items.append({
                        "product_id": product.id,
                        "available_stock": product.stock,
                        "requested_quantity": item.quantity
                    })

            if out_of_stock_items:
                return Response(
                    {
                        "detail": "Some products are out of stock.",
                        "out_of_stock": out_of_stock_items
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Deduct stock and calculate total
            for item in order.items.all():
                product = products_map[item.product.id]
                product.stock -= item.quantity
                product.save(update_fields=["stock"])
                order_total += product.price * item.quantity

            # Update order status & shipping address
            order.status = "processing"
            order.processing_at = timezone.now()
            order.shipping_address = shipping_address
            order.total_price = order_total
            order.save(update_fields=["status", "processing_at", "shipping_address", "total_price"])

            # Create payment record
            Payment.objects.create(
                user=request.user,
                order=order,
                reference=reference,
                amount=amount_paid,
                status="verified",
                provider_response=paystack_response["data"],
                verified_at=timezone.now(),
            )

        return Response(
            {
                "detail": "Payment verified and order finalized.",
                "order_id": str(order.public_id),  # return UUID to frontend
                "total_price": order_total
            },
            status=status.HTTP_201_CREATED
        )



class PaystackWebhookView(APIView):
    """
    Handles Paystack webhook events asynchronously.
    Acts as a safety net for any missed verifications.
    """
    permission_classes = []  # Public webhook

    def post(self, request):
        # Verify webhook signature
        signature = request.headers.get("x-paystack-signature")
        if not verify_webhook_signature(request.body, signature):
            return Response({"detail": "Invalid webhook signature."}, status=status.HTTP_400_BAD_REQUEST)

        event = request.data
        event_type = event.get("event")
        data = event.get("data", {})

        reference = data.get("reference")
        amount_paid = data.get("amount", 0) / 100

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

            payment.status = "verified"
            payment.verified_at = timezone.now()
            payment.amount = amount_paid
            payment.save(update_fields=["status", "verified_at", "amount"])

            order = payment.order
            order.status = "processing"
            order.processing_at = timezone.now()
            order.save(update_fields=["status", "processing_at"])

        return Response({"detail": "Webhook processed successfully."}, status=status.HTTP_200_OK)
