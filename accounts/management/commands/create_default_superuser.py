from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

User = get_user_model()

class Command(BaseCommand):
    help = "Create default superuser from env variables"

    def handle(self, *args, **kwargs):
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        display_name = os.environ.get("DJANGO_SUPERUSER_DISPLAY_NAME", "Admin")

        if not User.objects.filter(email=email).exists():
            User.objects.create_superuser(
                email=email,
                password=password,
                display_name=display_name,
            )
            self.stdout.write(self.style.SUCCESS(f"Superuser {email} created"))
        else:
            self.stdout.write(self.style.WARNING(f"Superuser {email} already exists"))
