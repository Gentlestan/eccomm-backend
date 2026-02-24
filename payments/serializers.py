from rest_framework import serializers
import uuid

class PaystackVerifySerializer(serializers.Serializer):
    """
    Serializer for verifying Paystack payments.

    Frontend should send:
    - reference: The Paystack transaction reference
    - pending_order_id: The server-generated UUID for the pending order
    - shipping_address: Street address
    - shipping_city: City
    - shipping_country: Country
    """

    reference = serializers.CharField(
        max_length=100,
        help_text="Paystack transaction reference",
    )
    pending_order_id = serializers.UUIDField(
        help_text="Server-generated pending order UUID"
    )

    # Shipping details
    shipping_address = serializers.CharField(
        required=True,
        max_length=255,
        help_text="Street address",
    )
    shipping_city = serializers.CharField(
        required=True,
        max_length=100,
        help_text="City",
    )
    shipping_country = serializers.CharField(
        required=True,
        max_length=100,
        help_text="Country",
    )

    def validate_reference(self, value):
        """
        Ensure reference is not blank or whitespace.
        """
        if not value.strip():
            raise serializers.ValidationError("Payment reference cannot be blank.")
        return value
