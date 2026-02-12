from django.db import models
from django.utils.text import slugify
from django.conf import settings
from cloudinary_storage.storage import MediaCloudinaryStorage

# ------------------------------
# Category model
# ------------------------------
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ------------------------------
# Product model
# ------------------------------
class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    brand = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    category = models.ForeignKey(Category, related_name="products", on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    rating = models.FloatField(default=0)
    staff_rating = models.FloatField(default=0)
    stock = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ------------------------------
# Product Image model
# ------------------------------
class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(
        upload_to="products/",
        storage=MediaCloudinaryStorage()  # Cloudinary storage
    )
    is_hero = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.product.name} Image"


# ------------------------------
# Review model (user-linked & moderated)
# ------------------------------
class Review(models.Model):
    product = models.ForeignKey(
        Product,
        related_name="reviews",
        on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="reviews",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField()
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("product", "user")

    def __str__(self):
        return f"{self.user.email} → {self.product.name}"


# ------------------------------
# Review Image model
# ------------------------------
class ReviewImage(models.Model):
    review = models.ForeignKey(Review, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(
        upload_to="reviews/",
        storage=MediaCloudinaryStorage()  # Cloudinary storage
    )

    def __str__(self):
        return f"Review Image for {self.review.user.email} → {self.review.product.name}"
