import uuid
from django.core.management.base import BaseCommand
from orders.models import Order
from django.db import transaction
from django.db import models


class Command(BaseCommand):
    help = "Fix duplicate public_id values in production database"

    def handle(self, *args, **kwargs):
        duplicates = (
            Order.objects.values('public_id')
            .annotate(count_id=models.Count('id'))
            .filter(count_id__gt=1)
        )

        if not duplicates.exists():
            self.stdout.write(self.style.SUCCESS("No duplicates found."))
            return

        self.stdout.write(f"Found {duplicates.count()} duplicates. Fixing...")
        with transaction.atomic():
            for dup in duplicates:
                orders = Order.objects.filter(public_id=dup['public_id']).order_by('id')
                # Keep the first order's public_id, fix the rest
                for order in orders[1:]:
                    old_id = order.public_id
                    order.public_id = uuid.uuid4()
                    order.save(update_fields=['public_id'])
                    self.stdout.write(f"Updated order {order.id} from {old_id} to {order.public_id}")

        self.stdout.write(self.style.SUCCESS("All duplicates fixed!"))
