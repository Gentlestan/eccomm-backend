from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

# 1️⃣ Custom manager
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


# 2️⃣ Custom user model
class CustomUser(AbstractUser):
    username = None  # remove username field
    email = models.EmailField(unique=True)
    display_name = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Name displayed publicly (e.g., on reviews)."
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        # If display_name exists, use it; otherwise fallback to email before @
        return self.display_name or self.email.split("@")[0]
