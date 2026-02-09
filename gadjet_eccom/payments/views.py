# payments/views.py

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
    Verify Paystack payment from frontend (sync verification),
    validate stock, create order & payment, deduct inventory.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaystackVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reference = serializer.validated_data["reference"]
        items = serializer.validated_data["items"]

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

        amount_paid = data.get("amount", 0) / 100  # Convert kobo → naira

        # Atomic transaction for order creation
        with transaction.atomic():
            order_total = 0
            out_of_stock_items = []

            # Lock product rows
            products_map = {
                p.id: p for p in Product.objects.select_for_update().filter(
                    id__in=[item["product_id"] for item in items]
                )
            }

            # Validate stock
            for item in items:
                product = products_map.get(item["product_id"])
                quantity = int(item["quantity"])

                if not product:
                    return Response(
                        {"detail": f"Product ID {item['product_id']} not found."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if quantity <= 0:
                    return Response(
                        {"detail": f"Invalid quantity for {product.name}."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if product.stock < quantity:
                    out_of_stock_items.append({
                        "product_id": product.id,
                        "product_name": product.name,
                        "available_stock": product.stock,
                        "requested_quantity": quantity,
                    })

            if out_of_stock_items:
                return Response(
                    {
                        "detail": "Some products are out of stock.",
                        "out_of_stock": out_of_stock_items,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Create order
            order = Order.objects.create(
                user=request.user,
                status="processing",
                processing_at=timezone.now(),
                total_price=0,
            )

            # Deduct stock and create order items
            for item in items:
                product = products_map[item["product_id"]]
                quantity = int(item["quantity"])

                product.stock -= quantity
                product.save(update_fields=["stock"])

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=product.price,
                )

                order_total += product.price * quantity

            # Record payment
            payment = Payment.objects.create(
                user=request.user,
                order=order,
                reference=reference,
                amount=amount_paid,
                status="verified",
                provider_response=data,
                verified_at=timezone.now(),
            )

            # Final amount check
            if order_total != amount_paid:
                payment.status = "failed"
                payment.save(update_fields=["status"])
                return Response(
                    {
                        "detail": "Payment amount does not match order total.",
                        "order_total": order_total,
                        "amount_paid": amount_paid,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            order.total_price = order_total
            order.save(update_fields=["total_price"])

        return Response(
            {
                "detail": "Payment verified and order created successfully.",
                "order_id": order.id,
                "total_price": order_total,
            },
            status=status.HTTP_201_CREATED,
        )


class PaystackWebhookView(APIView):
    """
    Handles Paystack webhook events asynchronously.
    Must configure the webhook URL in Paystack dashboard.
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
