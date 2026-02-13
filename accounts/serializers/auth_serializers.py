from rest_framework import serializers
from ..models import CustomUser
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.conf import settings
from django.core.mail import send_mail


# =====================================================
# Registration with Email Verification
# =====================================================
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    display_name = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50
    )

    class Meta:
        model = CustomUser
        fields = ("email", "password", "display_name")

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Email already exists. Please login instead."
            )
        return value

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            display_name=validated_data.get("display_name", ""),
            is_active=False,  # inactive until email verified
        )

        # Generate UID and token
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        verification_link = f"{frontend_url}/verify-email/{uid}/{token}"

        # Send verification email
        send_mail(
            subject="Verify your email for Gadget Express",
            message=(
                f"Hi {user.display_name or 'there'},\n\n"
                f"Click the link below to verify your email:\n\n"
                f"{verification_link}\n\n"
                "If you did not create this account, please ignore this email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return user


# =====================================================
# Email Verification
# =====================================================
class VerifyEmailSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()

    def validate(self, attrs):
        try:
            uid = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            raise serializers.ValidationError("Invalid verification link")

        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError("Invalid or expired token")

        attrs["user"] = user
        return attrs

    def save(self):
        user = self.validated_data["user"]
        user.is_active = True
        user.save()
        return user


# =====================================================
# Login
# =====================================================
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(email=data["email"], password=data["password"])

        if not user:
            raise serializers.ValidationError("Invalid email or password")

        if not user.is_active:
            raise serializers.ValidationError("Email not verified")

        data["user"] = user
        return data


# =====================================================
# Forgot Password (Send Reset Email)
# =====================================================
class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value  # do not reveal if email exists

    def save(self):
        email = self.validated_data["email"]
        user = CustomUser.objects.filter(email=email).first()

        # If user does not exist, silently return
        if not user:
            return None

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        reset_link = f"{frontend_url}/reset-password/{uid}/{token}"

        send_mail(
            subject="Reset your password for Gadget Express",
            message=(
                "You requested a password reset.\n\n"
                f"Click the link below to reset your password:\n\n"
                f"{reset_link}\n\n"
                "If you did not request this, please ignore this email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return reset_link



# =====================================================
# Reset Password
# =====================================================
class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)

    def validate(self, attrs):
        try:
            uid = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            raise serializers.ValidationError("Invalid reset link")

        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError("Invalid or expired token")

        attrs["user"] = user
        return attrs

    def save(self):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user
