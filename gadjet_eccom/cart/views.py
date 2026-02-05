from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import F

from .models import Cart, CartItem
from gadjet_shop.models import Product
from .serializers import (
    CartSerializer,
    AddUpdateCartItemSerializer,
    UpdateCartItemQuantitySerializer  # new serializer for PATCH
)


class CartViewSet(viewsets.ViewSet):
    """
    Production-ready Cart API matching frontend cart.
    Endpoints:
    - GET    /cart/                 -> get current user's cart
    - POST   /cart/add/             -> add item to cart
    - PATCH  /cart/update/<pk>/     -> update quantity
    - DELETE /cart/remove/<pk>/     -> remove item
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
        quantity = serializer.validated_data['quantity']

        product = get_object_or_404(Product, id=product_id)

        if product.stock < quantity:
            return Response(
                {"status": "error", "message": "Insufficient stock"},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart = self.get_cart(request.user)

        with transaction.atomic():
            item, created = CartItem.objects.select_for_update().get_or_create(
                cart=cart,
                product=product
            )
            if not created:
                item.quantity = F('quantity') + quantity
            else:
                item.quantity = quantity
            item.save()
            item.refresh_from_db()  # refresh F() value

        cart = self.get_cart(request.user)
        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response(cart_serializer.data, status=status.HTTP_201_CREATED)

    # PATCH /cart/update/<pk>/
    @action(detail=True, methods=['patch'], url_path='update')
    def update_item(self, request, pk=None):
        # Use the new serializer that only expects quantity
        serializer = UpdateCartItemQuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quantity = serializer.validated_data['quantity']

        with transaction.atomic():
            item = get_object_or_404(
                CartItem.objects.select_for_update(),
                id=pk,
                cart__user=request.user
            )

            if item.product.stock < quantity:
                return Response(
                    {"status": "error", "message": "Insufficient stock"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            item.quantity = quantity
            item.save()

        # Return full cart after update
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

        cart = self.get_cart(request.user)
        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response(cart_serializer.data, status=status.HTTP_200_OK)
