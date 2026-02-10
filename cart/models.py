from django.conf import settings
from django.db import models
from django.db.models import F, Sum, DecimalField, ExpressionWrapper
from django.core.exceptions import ValidationError
from gadjet_shop.models import Product


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

    @property
    def is_valid(self):
        """Check if all items are within available stock."""
        for item in self.items.all():
            if item.quantity > item.product.stock:
                return False
        return True


class CartItem(models.Model):
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

    @property
    def subtotal(self):
        """Total price for this item."""
        return self.quantity * self.product.price

    def __str__(self):
        return f"{self.quantity} × {self.product.name}"

    def clean(self):
        """Prevent adding more than available stock."""
        if self.quantity > self.product.stock:
            raise ValidationError(
                f"Cannot add {self.quantity} of {self.product.name}. Only {self.product.stock} in stock."
            )

    def save(self, *args, **kwargs):
        self.full_clean()  # calls clean() before saving
        super().save(*args, **kwargs)
