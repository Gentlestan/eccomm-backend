from rest_framework import serializers
import uuid

class PaystackVerifySerializer(serializers.Serializer):
    """
    Serializer for verifying Paystack payments.

    Frontend should send:
    - reference: The Paystack transaction reference
    - pending_order_id: The server-generated UUID for the pending order
    - shipping_address: Optional shipping info
    """

    reference = serializers.CharField(
        max_length=100,
        help_text="Paystack transaction reference",
    )
    pending_order_id = serializers.UUIDField(
        help_text="Server-generated pending order UUID"
    )
    shipping_address = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Optional shipping address"
    )

    def validate_reference(self, value):
        """
        Ensure reference is not blank or whitespace.
        """
        if not value.strip():
            raise serializers.ValidationError("Payment reference cannot be blank.")
        return value
