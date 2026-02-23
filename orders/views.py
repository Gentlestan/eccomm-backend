from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.utils import timezone

from .models import Order
from .serializers import (
    OrderSerializer,
    OrderCreateSerializer,
    CancelOrderSerializer,
    UpdateOrderStatusSerializer
)


# -----------------------------
# Create Order
# -----------------------------
class CreateOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = OrderCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

# -----------------------------
# Create Pending Order
# -----------------------------

class CreatePendingOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Create a pending order for the current user.
        Copies items from their cart, calculates total_price,
        saves the order and items in DB, and returns the order's public_id.
        """
        from cart.models import Cart, CartItem  # ensure cart app is imported
        from gadjet_shop.models import Product
        from orders.models import Order, OrderItem

        # Get the user's cart
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart).select_related("product")

        if not cart_items.exists():
            return Response({"error": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate stock and calculate total price
        total_price = 0
        for item in cart_items:
            if item.quantity > item.product.stock:
                return Response(
                    {"error": f"Product '{item.product.name}' is out of stock."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            total_price += item.quantity * float(item.product.price)

        # -----------------------------
        # Create pending Order in DB
        # -----------------------------
        order = Order.objects.create(
            user=request.user,
            total_price=total_price,
            status="pending"
        )

        # Create OrderItems
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )

        # Return public_id to frontend
        return Response({
            "pending_order_id": str(order.public_id),
            "items": [
                {
                    "product_id": item.product.id,
                    "name": item.product.name,
                    "quantity": item.quantity,
                    "price": float(item.price),
                }
                for item in order.items.all()
            ],
            "total_price": total_price
        }, status=status.HTTP_201_CREATED)

# -----------------------------
# User: List own orders
# -----------------------------
class UserOrdersView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by("-created_at")


# -----------------------------
# User: Order detail
# -----------------------------
class UserOrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "public_id"

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


# -----------------------------
# User: Cancel order
# -----------------------------
class CancelOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):  # rename `order_id` → `order_uuid` if you want
        try:
            order = Order.objects.get(public_id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=404)

        serializer = CancelOrderSerializer(
            data={"order_id": str(order.public_id)}, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Order cancelled successfully"}, status=200)

# -----------------------------
# Admin: Update order status
# -----------------------------
class UpdateOrderStatusView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, order_id):
        try:
            order = Order.objects.get(public_id=order_id)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=404)

        serializer = UpdateOrderStatusSerializer(
            data={"order_id": str(order.public_id), "status": request.data.get("status")}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": f"Order status updated to {serializer.validated_data['status']}"},
            status=200
        )
