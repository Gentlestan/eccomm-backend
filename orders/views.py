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
        and returns a server-trusted pending_order_id and items.
        """
        from cart.models import Cart, CartItem  # make sure your cart app is imported
        from gadjet_shop.models import Product
        import uuid

        # Get the user's cart
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart).select_related("product")

        if not cart_items.exists():
            return Response({"error": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST)

        # Build pending order data (not saved in DB yet, just a temporary server-trusted payload)
        items = []
        total_price = 0

        for item in cart_items:
            # Ensure requested quantity <= stock
            if item.quantity > item.product.stock:
                return Response(
                    {"error": f"Product '{item.product.name}' is out of stock."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            items.append({
                "product_id": item.product.id,
                "name": item.product.name,
                "quantity": item.quantity,
                "price": float(item.product.price),  # send as float for frontend
            })
            total_price += item.quantity * float(item.product.price)

        # Generate a unique pending_order_id
        pending_order_id = str(uuid.uuid4())

        # Return JSON for frontend
        return Response({
            "pending_order_id": pending_order_id,
            "items": items,
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
    lookup_field = "id"

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


# -----------------------------
# User: Cancel order
# -----------------------------
class CancelOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        serializer = CancelOrderSerializer(
            data={"order_id": order_id}, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Order cancelled successfully"}, status=status.HTTP_200_OK)


# -----------------------------
# Admin: Update order status
# -----------------------------
class UpdateOrderStatusView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, order_id):
        serializer = UpdateOrderStatusSerializer(
            data={"order_id": order_id, "status": request.data.get("status")}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": f"Order status updated to {serializer.validated_data['status']}"},
            status=status.HTTP_200_OK
        )
