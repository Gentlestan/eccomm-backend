from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from .models import Order, OrderItem
from gadjet_shop.models import Product, Review


# ------------------------------
# Review Summary Serializer (READ)
# ------------------------------
class ReviewSummarySerializer(serializers.ModelSerializer):
    user_display_name = serializers.SerializerMethodField()
    date = serializers.DateTimeField(source="created_at", format="%Y-%m-%d", read_only=True)

    class Meta:
        model = Review
        fields = ["user_display_name", "rating", "comment", "date"]

    def get_user_display_name(self, obj):
        if obj.user:
            return obj.user.display_name or obj.user.email.split("@")[0]
        return "Anonymous"


# ------------------------------
# Product Summary Serializer (READ)
# ------------------------------
class ProductSummarySerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "name", "price", "slug", "images", "reviews"]

    def get_images(self, obj):
        return [{"image": img.image.url} for img in obj.images.all()]

    def get_reviews(self, obj):
        reviews = obj.reviews.filter(is_approved=True).select_related("user")
        return ReviewSummarySerializer(reviews, many=True).data


# ------------------------------
# Order Item Serializer (READ)
# ------------------------------
class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSummarySerializer(read_only=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, coerce_to_string=False)

    class Meta:
        model = OrderItem
        fields = ["product", "quantity", "price"]


# ------------------------------
# Main Order Serializer (READ)
# ------------------------------
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, coerce_to_string=False)

    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    processing_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    shipped_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    delivered_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    cancelled_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "status", "created_at", "total_price",
            "processing_at", "shipped_at", "delivered_at", "cancelled_at",
            "items",
        ]
        read_only_fields = [
            "created_at", "processing_at", "shipped_at", "delivered_at",
            "cancelled_at", "total_price",
        ]


# ------------------------------
# Order Creation Serializer (WRITE)
# ------------------------------
class OrderItemCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.Serializer):
    items = OrderItemCreateSerializer(many=True)

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("Order must contain at least one item.")
        return items

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user
        items_data = validated_data["items"]

        total_price = 0
        order_items = []

        with transaction.atomic():
            product_ids = [item["product_id"] for item in items_data]
            products = Product.objects.select_for_update().filter(id__in=product_ids)
            products_map = {p.id: p for p in products}

            for item in items_data:
                product = products_map.get(item["product_id"])
                if not product:
                    raise serializers.ValidationError(f"Product with id {item['product_id']} not found.")
                if item["quantity"] > product.stock:
                    raise serializers.ValidationError(f"Not enough stock for {product.name}.")

                # Deduct stock
                product.stock -= item["quantity"]
                product.save()

                total_price += product.price * item["quantity"]
                order_items.append(OrderItem(product=product, quantity=item["quantity"], price=product.price))

            # Create order
            order = Order.objects.create(user=user, total_price=total_price)
            for oi in order_items:
                oi.order = order
            OrderItem.objects.bulk_create(order_items)

        return order


# ------------------------------
# Cancel Order Serializer (WRITE)
# ------------------------------
class CancelOrderSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()

    def validate_order_id(self, order_id):
        request = self.context["request"]
        try:
            order = Order.objects.select_for_update().get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            raise serializers.ValidationError("Order not found.")
        if order.status != "pending":
            raise serializers.ValidationError("Only pending orders can be cancelled.")
        return order_id

    def save(self):
        request = self.context["request"]
        order_id = self.validated_data["order_id"]

        with transaction.atomic():
            order = Order.objects.select_for_update().get(id=order_id, user=request.user)
            order.status = "cancelled"
            order.cancelled_at = timezone.now()
            order.save()

            # Rollback stock
            for item in order.items.select_related("product"):
                product = item.product
                product.stock += item.quantity
                product.save()

        return order


# ------------------------------
# Admin Order Status Update Serializer (WRITE)
# ------------------------------
class UpdateOrderStatusSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)

    def save(self):
        order_id = self.validated_data["order_id"]
        new_status = self.validated_data["status"]

        with transaction.atomic():
            order = Order.objects.select_for_update().get(id=order_id)
            order.status = new_status
            now = timezone.now()

            if new_status == "processing":
                order.processing_at = now
            elif new_status == "shipped":
                order.shipped_at = now
            elif new_status == "delivered":
                order.delivered_at = now
            elif new_status == "cancelled":
                order.cancelled_at = now

            order.save()
        return order
