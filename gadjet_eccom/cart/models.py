from django.conf import settings
from django.db import models
from django.db.models import F, Sum, DecimalField, ExpressionWrapper


class Cart(models.Model):
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
        )["total"] or 0


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        related_name="items",
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        "gadjet_shop.Product",
        related_name="cart_items",
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cart", "product")

    @property
    def subtotal(self):
        return self.quantity * self.product.price

    def __str__(self):
        return f"{self.quantity} × {self.product.name}"
