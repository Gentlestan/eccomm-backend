from django.contrib import admin
from .models import Product, ProductImage, Review, ReviewImage, Category
from orders.models import Order, OrderItem  # <-- add this

# -----------------------------
# Inline for Product Images
# -----------------------------
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ()

# -----------------------------
# Inline for Review Images
# -----------------------------
class ReviewImageInline(admin.TabularInline):
    model = ReviewImage
    extra = 1
    readonly_fields = ()

# -----------------------------
# Inline for Reviews on Product Admin
# -----------------------------
class ReviewInline(admin.TabularInline):
    model = Review
    extra = 1
    readonly_fields = ('created_at', 'user_display_name')
    fields = ('user_display_name', 'rating', 'comment', 'created_at', 'is_approved')

    def user_display_name(self, obj):
        if obj.user:
            return obj.user.display_name or obj.user.email.split("@")[0]
        return "Anonymous"
    user_display_name.short_description = "User"

# -----------------------------
# Product Admin
# -----------------------------
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'category', 'price', 'stock')
    list_filter = ('category', 'brand')
    search_fields = ('name', 'brand', 'category__name')
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductImageInline, ReviewInline]

# -----------------------------
# Category Admin
# -----------------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {"slug": ("name",)}

# -----------------------------
# Review Admin
# -----------------------------
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user_display_name', 'product', 'rating', 'is_approved', 'created_at')
    readonly_fields = ('user_display_name',)
    list_filter = ('is_approved', 'rating', 'created_at')
    search_fields = ('user__email', 'user__display_name', 'product__name', 'comment')
    list_editable = ('is_approved',)
    ordering = ('-created_at',)
    inlines = [ReviewImageInline]

    actions = ['approve_selected_reviews']

    def approve_selected_reviews(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"{updated} review(s) approved successfully.")

    approve_selected_reviews.short_description = "Approve selected reviews"

    def user_display_name(self, obj):
        if obj.user:
            return obj.user.display_name or obj.user.email.split("@")[0]
        return "Anonymous"
    user_display_name.short_description = "User"

# -----------------------------
# Review Image Admin
# -----------------------------
@admin.register(ReviewImage)
class ReviewImageAdmin(admin.ModelAdmin):
    list_display = ('review', 'image')

# -----------------------------
# Inline for Order Items
# -----------------------------
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price')
    can_delete = False

# -----------------------------
# Order Admin
# -----------------------------
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'total_price', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'user__display_name')
    inlines = [OrderItemInline]