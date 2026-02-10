from rest_framework import serializers

class PaystackItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)

class PaystackVerifySerializer(serializers.Serializer):
    reference = serializers.CharField(max_length=100)
    items = serializers.ListField(
        child=PaystackItemSerializer(),
        allow_empty=False,
        help_text="List of products with their quantities."
    )
    shipping_address = serializers.CharField(
        required=False, allow_blank=True, max_length=500
    )

    def validate_reference(self, value):
        if not value.strip():
            raise serializers.ValidationError("Payment reference cannot be blank.")
        return value
