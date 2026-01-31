# accounts/serializers/user_serializers.py

from rest_framework import serializers
from ..models import CustomUser

# ------------------------------
# Serializer for returning user info (/me/)
# ------------------------------
class UserSerializer(serializers.ModelSerializer):
    """
    Returns the authenticated user's profile information.
    Safe for frontend consumption.
    """
    class Meta:
        model = CustomUser
        fields = ("id", "email", "display_name")  # removed 'role'
        read_only_fields = ("id", "email")


# ------------------------------
# Serializer for updating profile
# ------------------------------
class UpdateProfileSerializer(serializers.ModelSerializer):
    """
    Allows user to update their profile fields.
    Only display_name is editable in this example.
    """
    display_name = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50,
    )

    class Meta:
        model = CustomUser
        fields = ("display_name",)

    def update(self, instance, validated_data):
        instance.display_name = validated_data.get("display_name", instance.display_name)
        instance.save()
        return instance


# ------------------------------
# Serializer for changing password
# ------------------------------
class ChangePasswordSerializer(serializers.Serializer):
    """
    Handles password update for authenticated users.
    Requires old password for verification.
    """
    old_password = serializers.CharField(write_only=True, min_length=8)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user
