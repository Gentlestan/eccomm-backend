from django.conf import settings
from rest_framework import serializers
from gadjet_shop.models import Product, ProductImage
from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    qty = serializers.IntegerField(source="quantity", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_price = serializers.DecimalField(
        source="product.price",
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    product_image = serializers.SerializerMethodField()
    subtotal = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = CartItem
        fields = (
            "id",
            "product",
            "product_name",
            "product_price",
            "product_image",
            "qty",
            "subtotal",
        )

    def get_product_image(self, obj):
        """
        Returns a full URL for the hero image or first image of the product.
        """
        # Get hero image first
        hero_image = obj.product.images.filter(is_hero=True).first()
        if hero_image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(hero_image.image.url)
            return f"{settings.MEDIA_URL}{hero_image.image.name}"

        # Fallback to first image
        first_image = obj.product.images.first()
        if first_image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(first_image.image.url)
            return f"{settings.MEDIA_URL}{first_image.image.name}"

        # No image → return placeholder
        return "/assets/images/placeholder.png"


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    totalQty = serializers.IntegerField(source="total_items", read_only=True)
    totalPrice = serializers.DecimalField(
        source="subtotal",
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = Cart
        fields = (
            "id",
            "items",
            "totalQty",
            "totalPrice",
        )


class AddUpdateCartItemSerializer(serializers.Serializer):
    """
    Serializer for adding items to the cart (POST /cart/add/)
    """
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)

    def validate_product_id(self, value):
        if not Product.objects.filter(id=value).exists():
            raise serializers.ValidationError("Product does not exist")
        return value


class UpdateCartItemQuantitySerializer(serializers.Serializer):
    """
    Serializer for updating quantity only (PATCH /cart/<id>/update/)
    """
    quantity = serializers.IntegerField(min_value=1)
