from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework.exceptions import ValidationError

from .models import Product, Review
from .serializers import ProductSerializer, ReviewSerializer


# ----------------------------------
# PUBLIC: List all products
# ----------------------------------
class ProductListAPIView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = {
        "category__name": ["exact", "icontains"],
        "brand": ["exact", "icontains"],
    }
    ordering_fields = ["price", "rating", "created_at"]
    ordering = ["price"]

    def get_queryset(self):
        queryset = Product.objects.all()
        is_hero = self.request.query_params.get("is_hero")
        if is_hero == "true":
            queryset = queryset.filter(images__is_hero=True).distinct()
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


# ----------------------------------
# PUBLIC: Product detail by slug
# ----------------------------------
class ProductDetailAPIView(generics.RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = "slug"
    permission_classes = [AllowAny]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


# ----------------------------------
# PUBLIC: List approved reviews for a product
# ----------------------------------
class ReviewListAPIView(generics.ListAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        product_id = self.kwargs.get("product_id")
        return (
            Review.objects
            .filter(product_id=product_id, is_approved=True)
            .select_related("user")
            .order_by("-created_at")  # newest first
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


# ----------------------------------
# PROTECTED: Create review (pending approval)
# ----------------------------------
class ReviewCreateAPIView(generics.CreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        from .models import Product  # ensure we get the product instance
        product_id = self.kwargs.get("product_id")

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise ValidationError({"product": "Product not found."})

        # The buyer-only check is handled in the serializer's validate() method
        serializer.save(
            user=self.request.user,
            product=product,
            is_approved=False  # pending admin approval
        )

    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        return Response(
            {"message": "Review submitted successfully and is pending admin approval"},
            status=status.HTTP_201_CREATED
        )
