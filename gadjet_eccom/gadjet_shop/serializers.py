from rest_framework import serializers
from .models import Product, ProductImage, Review, ReviewImage, Category
from django.contrib.auth import get_user_model
from orders.models import OrderItem  # to check if user bought the product

User = get_user_model()


# ------------------------------
# Category Serializer
# ------------------------------
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


# ------------------------------
# Product Image Serializer
# ------------------------------
class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['image']


# ------------------------------
# Review Image Serializer
# ------------------------------
class ReviewImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewImage
        fields = ['image']


# ------------------------------
# Review Serializer (with buyer-only validation)
# ------------------------------
class ReviewSerializer(serializers.ModelSerializer):
    images = ReviewImageSerializer(many=True, read_only=True)
    date = serializers.DateTimeField(source='created_at', read_only=True, format="%Y-%m-%d")
    user_display_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['id', 'user_display_name', 'rating', 'comment', 'date', 'images', 'is_approved', 'product']
        read_only_fields = ['is_approved', 'product']

    def get_user_display_name(self, obj):
        if obj.user:
            return obj.user.display_name or obj.user.email.split("@")[0]
        return "Anonymous"

    def validate(self, attrs):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        product = attrs.get('product')

        if user is None or not user.is_authenticated:
            raise serializers.ValidationError("Authentication required to submit a review.")

        # Check if user has purchased this product
        has_bought = OrderItem.objects.filter(
            order__user=user,
            order__status__in=['pending', 'processing', 'shipped', 'delivered'],
            product=product
        ).exists()

        if not has_bought:
            raise serializers.ValidationError("You can only review products you have purchased.")

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        validated_data['is_approved'] = False
        return super().create(validated_data)


# ------------------------------
# Product Serializer (nested reviews)
# ------------------------------
class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    reviews = serializers.SerializerMethodField()
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'description',
            'brand',
            'slug',
            'category',
            'price',
            'rating',
            'staff_rating',
            'stock',
            'images',
            'reviews',
        ]

    def get_reviews(self, obj):
        # Only approved reviews
        reviews = Review.objects.filter(product=obj, is_approved=True).select_related("user")
        return ReviewSerializer(reviews, many=True).data
