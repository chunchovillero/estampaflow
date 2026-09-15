import uuid
from django.conf import settings
from django.db import models
from django.utils.text import slugify

class Business(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        ACTIVE = "active", "Activa"
        SUSPENDED = "suspended", "Suspendida"
        REJECTED = "rejected", "Rechazada"
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    legal_name = models.CharField(max_length=200, blank=True)
    rut = models.CharField(max_length=12, blank=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to="businesses/logos/", blank=True)
    banner = models.ImageField(upload_to="businesses/banners/", blank=True)
    primary_color = models.CharField(max_length=7, default="#5B4CF0")
    secondary_color = models.CharField(max_length=7, default="#12B886")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)
    instagram = models.CharField(max_length=80, blank=True)
    website = models.URLField(blank=True)
    address = models.CharField(max_length=240, blank=True)
    commune = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    coverage = models.TextField(blank=True)
    allows_pickup = models.BooleanField(default=True)
    local_delivery = models.BooleanField(default=False)
    national_delivery = models.BooleanField(default=False)
    currency = models.CharField(max_length=3, default="CLP")
    timezone = models.CharField(max_length=50, default="America/Santiago")
    opening_hours = models.JSONField(default=dict, blank=True)
    average_response_hours = models.PositiveSmallIntegerField(default=24)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    is_verified = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)
    accepts_quotes = models.BooleanField(default=True)
    weekly_capacity = models.PositiveIntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "emprendimiento"
            candidate = base
            while Business.objects.exclude(pk=self.pk).filter(slug=candidate).exists():
                candidate = f"{base}-{uuid.uuid4().hex[:6]}"
            self.slug = candidate
        super().save(*args, **kwargs)
    def __str__(self): return self.name

class BusinessSetting(models.Model):
    business = models.OneToOneField(Business, on_delete=models.CASCADE, related_name="settings")
    order_prefix = models.CharField(max_length=10, default="PED")
    next_order_number = models.PositiveIntegerField(default=1)
    whatsapp_templates = models.JSONField(default=dict, blank=True)
    payment_methods = models.JSONField(default=list, blank=True)
    delivery_methods = models.JSONField(default=list, blank=True)

class BusinessMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Propietario"
        COLLABORATOR = "collaborator", "Colaborador"
    business = models.ForeignKey(Business, on_delete=models.PROTECT, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="memberships")
    role = models.CharField(max_length=20, choices=Role.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=("business", "user"), name="unique_business_membership")]

class Plan(models.Model):
    code=models.SlugField(unique=True)
    name=models.CharField(max_length=80)
    monthly_price=models.DecimalField(max_digits=10,decimal_places=0,default=0)
    limits=models.JSONField(default=dict,help_text="Límites: orders, public_products, users, storage_mb, quote_responses")
    is_active=models.BooleanField(default=True)
    position=models.PositiveSmallIntegerField(default=0)
    def __str__(self):return self.name

class Subscription(models.Model):
    business=models.OneToOneField(Business,on_delete=models.PROTECT,related_name="subscription")
    plan=models.ForeignKey(Plan,on_delete=models.PROTECT,related_name="subscriptions")
    status=models.CharField(max_length=12,choices=[("active","Activa"),("trial","Prueba"),("suspended","Suspendida"),("cancelled","Cancelada")],default="active")
    starts_at=models.DateTimeField(auto_now_add=True)
    ends_at=models.DateTimeField(null=True,blank=True)
    overrides=models.JSONField(default=dict,blank=True)
    def limit(self,key):return self.overrides.get(key,self.plan.limits.get(key))
