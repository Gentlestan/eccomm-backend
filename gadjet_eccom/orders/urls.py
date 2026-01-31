from django.urls import path
from .views import (
    CreateOrderView,
    UserOrdersView,
    UserOrderDetailView,
    CancelOrderView,
    UpdateOrderStatusView,
)

urlpatterns = [
    path("", CreateOrderView.as_view(), name="create-order"),  # POST
    path("my-orders/", UserOrdersView.as_view(), name="user-orders"),  # GET
    path("my-orders/<int:id>/", UserOrderDetailView.as_view(), name="user-order-detail"),  # GET
    path("my-orders/<int:order_id>/cancel/", CancelOrderView.as_view(), name="cancel-order"),  # POST
    path("admin/<int:order_id>/update-status/", UpdateOrderStatusView.as_view(), name="update-order-status"),  # PATCH
]
