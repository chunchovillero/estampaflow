from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="Business", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("name", models.CharField(max_length=160)),
            ("slug", models.SlugField(blank=True, max_length=180, unique=True)), ("legal_name", models.CharField(blank=True, max_length=200)), ("rut", models.CharField(blank=True, max_length=12)),
            ("description", models.TextField(blank=True)), ("logo", models.ImageField(blank=True, upload_to="businesses/logos/")), ("banner", models.ImageField(blank=True, upload_to="businesses/banners/")),
            ("primary_color", models.CharField(default="#5B4CF0", max_length=7)), ("secondary_color", models.CharField(default="#12B886", max_length=7)), ("email", models.EmailField(blank=True, max_length=254)),
            ("phone", models.CharField(blank=True, max_length=20)), ("whatsapp", models.CharField(blank=True, max_length=20)), ("instagram", models.CharField(blank=True, max_length=80)),
            ("website", models.URLField(blank=True)), ("address", models.CharField(blank=True, max_length=240)), ("commune", models.CharField(blank=True, max_length=100)), ("region", models.CharField(blank=True, max_length=100)),
            ("coverage", models.TextField(blank=True)), ("allows_pickup", models.BooleanField(default=True)), ("local_delivery", models.BooleanField(default=False)), ("national_delivery", models.BooleanField(default=False)),
            ("currency", models.CharField(default="CLP", max_length=3)), ("timezone", models.CharField(default="America/Santiago", max_length=50)), ("opening_hours", models.JSONField(blank=True, default=dict)),
            ("average_response_hours", models.PositiveSmallIntegerField(default=24)), ("status", models.CharField(choices=[("pending", "Pendiente"), ("active", "Activa"), ("suspended", "Suspendida"), ("rejected", "Rechazada")], default="pending", max_length=12)),
            ("is_verified", models.BooleanField(default=False)), ("is_public", models.BooleanField(default=False)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
        ]),
        migrations.CreateModel(name="BusinessMembership", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("role", models.CharField(choices=[("owner", "Propietario"), ("collaborator", "Colaborador")], max_length=20)),
            ("is_active", models.BooleanField(default=True)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("business", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="memberships", to="businesses.business")),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="memberships", to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name="BusinessSetting", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("order_prefix", models.CharField(default="PED", max_length=10)),
            ("next_order_number", models.PositiveIntegerField(default=1)), ("whatsapp_templates", models.JSONField(blank=True, default=dict)), ("payment_methods", models.JSONField(blank=True, default=list)),
            ("delivery_methods", models.JSONField(blank=True, default=list)), ("business", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="settings", to="businesses.business")),
        ]),
        migrations.AddConstraint(model_name="businessmembership", constraint=models.UniqueConstraint(fields=("business", "user"), name="unique_business_membership")),
    ]
