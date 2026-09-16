import uuid
from django.db import migrations,models

def fill_tokens(apps,schema_editor):
    Order=apps.get_model("operations","Order")
    for order in Order.objects.filter(public_access_token__isnull=True).iterator():
        order.public_access_token=uuid.uuid4()
        order.save(update_fields=["public_access_token"])

class Migration(migrations.Migration):
    dependencies=[("operations","0010_productimage")]
    operations=[
        migrations.AddField(model_name="order",name="public_access_token",field=models.UUIDField(null=True,editable=False)),
        migrations.RunPython(fill_tokens,migrations.RunPython.noop),
        migrations.AlterField(model_name="order",name="public_access_token",field=models.UUIDField(default=uuid.uuid4,unique=True,editable=False)),
    ]
