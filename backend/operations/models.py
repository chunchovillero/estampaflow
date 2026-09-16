import uuid
from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from businesses.models import Business

class TenantModel(models.Model):
    business = models.ForeignKey(Business, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta: abstract = True

class Customer(TenantModel):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20)
    whatsapp = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    instagram = models.CharField(max_length=80, blank=True)
    address = models.CharField(max_length=240, blank=True)
    commune = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    class Meta: ordering = ("first_name", "last_name")
    @property
    def full_name(self): return f"{self.first_name} {self.last_name}".strip()
    def __str__(self): return self.full_name

class ProductCategory(TenantModel):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    class Meta:
        ordering = ("name",)
        constraints = [models.UniqueConstraint(fields=("business", "name"), name="unique_category_per_business")]
    def __str__(self): return self.name

class Product(TenantModel):
    class PriceType(models.TextChoices):
        FIXED="fixed", "Fijo"
        FROM="from", "Desde"
        QUANTITY="quantity", "Por cantidad"
        QUOTE="quote", "Solo cotización"
    class ModerationStatus(models.TextChoices):
        PENDING="pending", "Pendiente"
        APPROVED="approved", "Aprobado"
        REJECTED="rejected", "Rechazado"
        HIDDEN="hidden", "Oculto"
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180)
    category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT, related_name="products")
    short_description = models.CharField(max_length=240, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="products/", blank=True)
    internal_cost = models.DecimalField(max_digits=12, decimal_places=0, default=0, validators=[MinValueValidator(Decimal("0"))])
    sale_price = models.DecimalField(max_digits=12, decimal_places=0, default=0, validators=[MinValueValidator(Decimal("0"))])
    price_type = models.CharField(max_length=12, choices=PriceType.choices, default=PriceType.FIXED)
    minimum_quantity = models.PositiveIntegerField(default=1)
    production_days = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=False)
    moderation_status = models.CharField(max_length=10,choices=ModerationStatus.choices,default=ModerationStatus.PENDING)
    track_stock = models.BooleanField(default=False)
    stock = models.IntegerField(default=0)
    techniques = models.JSONField(default=list, blank=True)
    customization_options = models.JSONField(default=list, blank=True)
    class Meta:
        ordering = ("name",)
        constraints = [models.UniqueConstraint(fields=("business", "slug"), name="unique_product_slug_per_business")]
    def __str__(self): return self.name

class ProductVariant(TenantModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    name = models.CharField(max_length=120)
    attributes = models.JSONField(default=dict, help_text="Ej.: talla, color, material o capacidad")
    sku = models.CharField(max_length=80, blank=True)
    price_adjustment = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    stock = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    class Meta: ordering = ("name",)

class Order(TenantModel):
    class Status(models.TextChoices):
        NEW="new", "Nuevo"
        WAITING_DESIGN="waiting_design", "Esperando diseño"
        WAITING_APPROVAL="waiting_approval", "Esperando aprobación"
        CHANGES="changes_requested", "Cambios solicitados"
        APPROVED="approved", "Aprobado"
        PRODUCTION="production", "En producción"
        READY="ready", "Listo"
        DELIVERED="delivered", "Entregado"
        CANCELLED="cancelled", "Cancelado"
    class Priority(models.TextChoices):
        LOW="low", "Baja"
        NORMAL="normal", "Normal"
        HIGH="high", "Alta"
        URGENT="urgent", "Urgente"
    class Origin(models.TextChoices):
        MANUAL="manual", "Manual"
        WHATSAPP="whatsapp", "WhatsApp"
        INSTAGRAM="instagram", "Instagram"
        PUBLIC_STORE="public_store", "Tienda pública"
        MARKETPLACE="marketplace", "Marketplace"
        QUOTE="quote", "Cotización"
    number = models.PositiveIntegerField()
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="orders")
    origin = models.CharField(max_length=20, choices=Origin.choices, default=Origin.MANUAL)
    due_date = models.DateField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.NEW)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.NORMAL)
    responsible = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="assigned_orders", null=True, blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=0, default=0, validators=[MinValueValidator(Decimal("0"))])
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=0, default=0, validators=[MinValueValidator(Decimal("0"))])
    total = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    total_paid = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    balance = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    payment_status = models.CharField(max_length=10, default="pending", choices=[("pending","Pendiente"),("partial","Abonado"),("paid","Pagado")])
    delivery_method = models.CharField(max_length=30, default="pickup")
    delivery_address = models.CharField(max_length=240, blank=True)
    customer_instructions = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    class Meta:
        ordering = ("-created_at",)
        constraints = [models.UniqueConstraint(fields=("business", "number"), name="unique_order_number_per_business")]
    @property
    def display_number(self): return f"PED-{self.number:05d}"

class OrderItem(TenantModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items", null=True, blank=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, related_name="order_items", null=True, blank=True)
    description = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_cost = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    unit_price = models.DecimalField(max_digits=12, decimal_places=0, validators=[MinValueValidator(Decimal("0"))])
    customizations = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    @property
    def line_total(self): return self.quantity * self.unit_price

class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="status_history")
    from_status = models.CharField(max_length=24, blank=True)
    to_status = models.CharField(max_length=24)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    comment = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ("-created_at",)

class Payment(TenantModel):
    class Method(models.TextChoices):
        TRANSFER="transfer", "Transferencia"
        CASH="cash", "Efectivo"
        DEBIT="debit", "Débito"
        CREDIT="credit", "Crédito"
        OTHER="other", "Otro"
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=0, validators=[MinValueValidator(Decimal("1"))])
    paid_at = models.DateTimeField()
    method = models.CharField(max_length=12, choices=Method.choices)
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    registered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    is_void = models.BooleanField(default=False)
    class Meta: ordering = ("-paid_at",)

class FeaturedBusiness(models.Model):
    business=models.ForeignKey(Business,on_delete=models.CASCADE,related_name="featured_placements")
    position=models.PositiveSmallIntegerField(default=0)
    starts_at=models.DateTimeField(null=True,blank=True)
    ends_at=models.DateTimeField(null=True,blank=True)
    is_active=models.BooleanField(default=True)
    reason=models.CharField(max_length=200,blank=True)
    is_paid=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=("position","-created_at")

class FeaturedProduct(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name="featured_placements")
    position=models.PositiveSmallIntegerField(default=0)
    starts_at=models.DateTimeField(null=True,blank=True)
    ends_at=models.DateTimeField(null=True,blank=True)
    is_active=models.BooleanField(default=True)
    reason=models.CharField(max_length=200,blank=True)
    is_paid=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=("position","-created_at")

class QuoteRequest(models.Model):
    class Status(models.TextChoices):
        OPEN="open","Abierta"
        PROPOSALS="proposals","Con propuestas"
        ACCEPTED="accepted","Aceptada"
        CLOSED="closed","Cerrada"
        CANCELLED="cancelled","Cancelada"
    public_id=models.UUIDField(default=uuid.uuid4,unique=True,editable=False)
    access_token=models.UUIDField(default=uuid.uuid4,unique=True,editable=False)
    title=models.CharField(max_length=180)
    category=models.CharField(max_length=100)
    product_type=models.CharField(max_length=120,blank=True)
    description=models.TextField()
    quantity=models.PositiveIntegerField(validators=[MinValueValidator(1)])
    specifications=models.JSONField(default=dict,blank=True)
    approximate_budget=models.DecimalField(max_digits=12,decimal_places=0,null=True,blank=True)
    required_date=models.DateField(null=True,blank=True)
    region=models.CharField(max_length=100)
    commune=models.CharField(max_length=100,blank=True)
    delivery_method=models.CharField(max_length=20,default="shipping")
    delivery_scope=models.CharField(max_length=30,blank=True)
    contact_name=models.CharField(max_length=160)
    contact_email=models.EmailField()
    contact_phone=models.CharField(max_length=20)
    contact_whatsapp=models.CharField(max_length=20,blank=True)
    status=models.CharField(max_length=12,choices=Status.choices,default=Status.OPEN)
    accepted_proposal=models.OneToOneField("QuoteProposal",on_delete=models.PROTECT,null=True,blank=True,related_name="accepted_for")
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=("-created_at",)

class QuoteMatch(models.Model):
    request=models.ForeignKey(QuoteRequest,on_delete=models.CASCADE,related_name="matches")
    business=models.ForeignKey(Business,on_delete=models.PROTECT,related_name="quote_matches")
    score=models.PositiveSmallIntegerField(default=0)
    reasons=models.JSONField(default=list)
    is_active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=("-score","created_at")
        constraints=[models.UniqueConstraint(fields=("request","business"),name="unique_quote_match")]

class QuoteProposal(models.Model):
    class Status(models.TextChoices):
        DRAFT="draft","Borrador"
        SENT="sent","Enviada"
        VIEWED="viewed","Vista"
        ACCEPTED="accepted","Aceptada"
        REJECTED="rejected","Rechazada"
        EXPIRED="expired","Vencida"
        WITHDRAWN="withdrawn","Retirada"
    public_id=models.UUIDField(default=uuid.uuid4,unique=True,editable=False)
    request=models.ForeignKey(QuoteRequest,on_delete=models.PROTECT,related_name="proposals")
    business=models.ForeignKey(Business,on_delete=models.PROTECT,related_name="quote_proposals")
    total_price=models.DecimalField(max_digits=12,decimal_places=0,validators=[MinValueValidator(Decimal("1"))])
    unit_price=models.DecimalField(max_digits=12,decimal_places=0,default=0)
    discount=models.DecimalField(max_digits=12,decimal_places=0,default=0)
    shipping_cost=models.DecimalField(max_digits=12,decimal_places=0,default=0)
    production_days=models.PositiveSmallIntegerField()
    estimated_delivery=models.DateField(null=True,blank=True)
    materials=models.CharField(max_length=240,blank=True)
    technique=models.CharField(max_length=100,blank=True)
    payment_terms=models.CharField(max_length=240,blank=True)
    deposit_percentage=models.PositiveSmallIntegerField(default=50)
    valid_until=models.DateField()
    comments=models.TextField(blank=True)
    status=models.CharField(max_length=12,choices=Status.choices,default=Status.SENT)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=("total_price","production_days")
        constraints=[models.UniqueConstraint(fields=("request","business"),name="unique_proposal_per_business")]

class Conversation(models.Model):
    proposal=models.OneToOneField(QuoteProposal,on_delete=models.CASCADE,related_name="conversation")
    created_at=models.DateTimeField(auto_now_add=True)

class Message(models.Model):
    conversation=models.ForeignKey(Conversation,on_delete=models.CASCADE,related_name="messages")
    sender_type=models.CharField(max_length=10,choices=[("client","Cliente"),("business","Empresa")])
    sender_user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,blank=True)
    body=models.TextField()
    file=models.ForeignKey("QuoteFile",on_delete=models.PROTECT,related_name="messages",null=True,blank=True)
    is_read=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=("created_at",)

class QuoteFile(models.Model):
    request=models.ForeignKey(QuoteRequest,on_delete=models.PROTECT,related_name="files")
    proposal=models.ForeignKey(QuoteProposal,on_delete=models.PROTECT,related_name="files",null=True,blank=True)
    business=models.ForeignKey(Business,on_delete=models.PROTECT,related_name="quote_files",null=True,blank=True)
    file=models.FileField(upload_to="quotes/%Y/%m/")
    original_name=models.CharField(max_length=255)
    mime_type=models.CharField(max_length=100)
    size=models.PositiveIntegerField()
    sender_type=models.CharField(max_length=10,choices=[("client","Cliente"),("business","Empresa")])
    uploaded_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,blank=True)
    is_active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=("created_at",)

class OrderFile(TenantModel):
    class Kind(models.TextChoices):
        CLIENT="client","Archivo del cliente"
        REFERENCE="reference","Referencia"
        DRAFT="draft","Borrador"
        FINAL="final","Diseño final"
        RECEIPT="receipt","Comprobante"
        FINISHED="finished","Producto terminado"
    order=models.ForeignKey(Order,on_delete=models.PROTECT,related_name="files")
    item=models.ForeignKey(OrderItem,on_delete=models.PROTECT,related_name="files",null=True,blank=True)
    file=models.FileField(upload_to="orders/%Y/%m/")
    kind=models.CharField(max_length=12,choices=Kind.choices)
    original_name=models.CharField(max_length=255)
    mime_type=models.CharField(max_length=100)
    size=models.PositiveIntegerField()
    uploaded_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,blank=True)
    is_active=models.BooleanField(default=True)

class DesignApproval(models.Model):
    order=models.ForeignKey(Order,on_delete=models.PROTECT,related_name="approvals")
    token=models.UUIDField(default=uuid.uuid4,unique=True,editable=False)
    expires_at=models.DateTimeField(null=True,blank=True)
    revoked_at=models.DateTimeField(null=True,blank=True)
    approved_at=models.DateTimeField(null=True,blank=True)
    approved_by_name=models.CharField(max_length=160,blank=True)
    comment=models.TextField(blank=True)
    ip_address=models.GenericIPAddressField(null=True,blank=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    created_at=models.DateTimeField(auto_now_add=True)
    @property
    def is_available(self):return not self.revoked_at and not self.approved_at and (not self.expires_at or self.expires_at>timezone.now())

class DesignChangeRequest(models.Model):
    approval=models.ForeignKey(DesignApproval,on_delete=models.PROTECT,related_name="change_requests")
    requested_by_name=models.CharField(max_length=160)
    comment=models.TextField()
    ip_address=models.GenericIPAddressField(null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    resolved_at=models.DateTimeField(null=True,blank=True)
    class Meta: ordering=("-created_at",)

class AuditLog(models.Model):
    business=models.ForeignKey(Business,on_delete=models.PROTECT,related_name="audit_logs",null=True,blank=True)
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="audit_logs",null=True,blank=True)
    action=models.CharField(max_length=80)
    entity_type=models.CharField(max_length=80)
    entity_id=models.CharField(max_length=80,blank=True)
    metadata=models.JSONField(default=dict,blank=True)
    ip_address=models.GenericIPAddressField(null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=("-created_at",)

class Notification(models.Model):
    business=models.ForeignKey(Business,on_delete=models.PROTECT,related_name="notifications")
    recipient=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="notifications")
    kind=models.CharField(max_length=40)
    title=models.CharField(max_length=160)
    body=models.CharField(max_length=300,blank=True)
    url=models.CharField(max_length=240,blank=True)
    read_at=models.DateTimeField(null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=("-created_at",)
