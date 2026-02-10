from django.urls import path
from .views import (
    ProductListAPIView,
    ProductDetailAPIView,
    ReviewListAPIView,
    ReviewCreateAPIView,
)

urlpatterns = [
    # Product endpoints
    path('products/', ProductListAPIView.as_view(), name='product-list'),
    path('products/<slug:slug>/', ProductDetailAPIView.as_view(), name='product-detail'),

    # Review endpoints
    path('products/<int:product_id>/reviews/', ReviewListAPIView.as_view(), name='review-list'),
    path('products/<int:product_id>/reviews/create/', ReviewCreateAPIView.as_view(), name='review-create'),
]
