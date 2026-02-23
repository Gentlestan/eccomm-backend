from django.db import migrations
import uuid

def fill_public_id(apps, schema_editor):
    Order = apps.get_model('orders', 'Order')
    for order in Order.objects.filter(public_id__isnull=True):
        order.public_id = uuid.uuid4()
        order.save()

class Migration(migrations.Migration):
    dependencies = [
        ('orders', '0002_order_public_id'),
    ]

    operations = [
        migrations.RunPython(fill_public_id),
    ]
