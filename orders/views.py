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
