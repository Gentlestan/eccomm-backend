from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import F, Sum

from .models import Cart, CartItem
from gadjet_shop.models import Product
from .serializers import (
    CartSerializer,
    AddUpdateCartItemSerializer,
    UpdateCartItemQuantitySerializer
)


class CartViewSet(viewsets.ViewSet):
    """
    Production-ready Cart API matching frontend cart.
    Endpoints:
    - GET    /cart/                 -> get current user's cart
    - POST   /cart/add/             -> add item to cart
    - PATCH  /cart/update/<pk>/     -> update quantity
    - DELETE /cart/remove/<pk>/     -> remove item
    - GET    /cart/validate/        -> validate cart stock before payment
    """
    permission_classes = [IsAuthenticated]

    def get_cart(self, user):
        """Helper: Get or create a cart for a user."""
        cart, _ = Cart.objects.get_or_create(user=user)
        return cart

    # GET /cart/
    def list(self, request):
        cart = self.get_cart(request.user)
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    # POST /cart/add/
    @action(detail=False, methods=['post'])
    def add(self, request):
        serializer = AddUpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_id = serializer.validated_data['product_id']
        quantity_to_add = serializer.validated_data['quantity']

        product = get_object_or_404(Product, id=product_id)
        cart = self.get_cart(request.user)

        with transaction.atomic():
            # Lock the CartItem row if exists
            item, created = CartItem.objects.select_for_update().get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': 0}
            )

            # Check combined quantity
            new_quantity = item.quantity + quantity_to_add
            if new_quantity > product.stock:
                available = max(product.stock - item.quantity, 0)
                return Response(
                    {
                        "status": "error",
                        "message": f"Cannot add {quantity_to_add} items. Only {available} left in stock."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            item.quantity = new_quantity
            item.save()
            item.refresh_from_db()  # refresh F() values

        # Return updated cart
        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response(cart_serializer.data, status=status.HTTP_201_CREATED)

    # PATCH /cart/update/<pk>/
    @action(detail=True, methods=['patch'], url_path='update')
    def update_item(self, request, pk=None):
        serializer = UpdateCartItemQuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_quantity = serializer.validated_data['quantity']

        with transaction.atomic():
            item = get_object_or_404(
                CartItem.objects.select_for_update(),
                id=pk,
                cart__user=request.user
            )

            if new_quantity > item.product.stock:
                return Response(
                    {
                        "status": "error",
                        "message": f"Cannot set quantity to {new_quantity}. Only {item.product.stock} available."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            item.quantity = new_quantity
            item.save()

        # Return updated cart
        cart = self.get_cart(request.user)
        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response(cart_serializer.data, status=status.HTTP_200_OK)

    # DELETE /cart/remove/<pk>/
    @action(detail=True, methods=['delete'], url_path='remove')
    def remove_item(self, request, pk=None):
        with transaction.atomic():
            item = get_object_or_404(
                CartItem.objects.select_for_update(),
                id=pk,
                cart__user=request.user
            )
            item.delete()

        # Return updated cart
        cart = self.get_cart(request.user)
        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response(cart_serializer.data, status=status.HTTP_200_OK)

    # NEW: GET /cart/validate/
    @action(detail=False, methods=['get'])
    def validate(self, request):
        """
        Validate the user's cart before payment.
        Returns out-of-stock items and whether the cart is valid.
        """
        cart = self.get_cart(request.user)
        cart_items = CartItem.objects.filter(cart=cart).select_related("product")

        out_of_stock = []
        for item in cart_items:
            if item.quantity > item.product.stock:
                out_of_stock.append({
                    "product_id": item.product.id,
                    "product_name": item.product.name,
                    "requested_quantity": item.quantity,
                    "available_stock": item.product.stock,
                })

        if out_of_stock:
            return Response({
                "valid": False,
                "out_of_stock": out_of_stock
            }, status=status.HTTP_200_OK)

        return Response({"valid": True, "message": "All items in stock."}, status=status.HTTP_200_OK)
