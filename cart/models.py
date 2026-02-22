from decimal import Decimal
from django.conf import settings
from django.db import models
from django.db.models import F, Sum, DecimalField, ExpressionWrapper
from django.core.exceptions import ValidationError
from django.utils import timezone
from gadjet_shop.models import Product


class Cart(models.Model):
    """
    Stores a shopping cart per user.
    Cart items are added here before creating a PendingOrder for payment.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="cart",
        on_delete=models.CASCADE,
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart ({self.user.email})"

    @property
    def total_items(self):
        """Total quantity of items in the cart."""
        return self.items.aggregate(total=Sum("quantity"))["total"] or 0

    @property
    def subtotal(self):
        """Subtotal of the cart (sum of quantity × product price)."""
        return self.items.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F("quantity") * F("product__price"),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )
            )
        )["total"] or Decimal("0.00")

    @property
    def is_valid(self):
        """
        Check if all items are within available stock.
        True if all items are available; False otherwise.
        """
        for item in self.items.all():
            if item.quantity > item.product.stock:
                return False
        return True

    def clear(self):
        """Clear all items in the cart."""
        self.items.all().delete()


class CartItem(models.Model):
    """
    Represents a product added to the cart.
    """
    cart = models.ForeignKey(
        Cart,
        related_name="items",
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        Product,
        related_name="cart_items",
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cart", "product")
        ordering = ["-added_at"]

    def __str__(self):
        return f"{self.quantity} × {self.product.name}"

    @property
    def subtotal(self):
        """Total price for this cart item."""
        return self.quantity * self.product.price

    def clean(self):
        """Prevent adding more than available stock."""
        if self.quantity > self.product.stock:
            raise ValidationError(
                f"Cannot add {self.quantity} of {self.product.name}. Only {self.product.stock} in stock."
            )

    def save(self, *args, **kwargs):
        self.full_clean()  # calls clean() before saving
        super().save(*args, **kwargs)


# -------------------------------
# Pending Order Models (Server-side trusted snapshot)
# -------------------------------

class PendingOrder(models.Model):
    """
    Stores a server-trusted snapshot of the cart before payment.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"PendingOrder({self.user.email}, id={self.id}, paid={self.is_paid})"

    def calculate_total(self):
        """Compute total price based on linked PendingOrderItems."""
        total = sum([item.subtotal for item in self.items.all()], Decimal("0.00"))
        self.total_price = total
        self.save(update_fields=["total_price"])
        return self.total_price


class PendingOrderItem(models.Model):
    """
    Individual items inside a PendingOrder.
    """
    pending_order = models.ForeignKey(PendingOrder, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # snapshot price

    class Meta:
        unique_together = ("pending_order", "product")

    @property
    def subtotal(self):
        """Total price for this pending order item."""
        return self.price * self.quantity

    def __str__(self):
        return f"{self.quantity} × {self.product.name}"
