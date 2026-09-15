from django.db import transaction
from django.utils.text import slugify
from rest_framework import serializers
from django.utils import timezone
from businesses.permissions import get_membership
from .models import Conversation,Customer,DesignApproval,DesignChangeRequest,Message,Order,OrderFile,OrderItem,OrderStatusHistory,Payment,Product,ProductCategory,ProductVariant,QuoteProposal,QuoteRequest
from .services import enforce_plan_limit,match_quote_request,next_order_number,recalculate_order,record_audit

class CustomerSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    class Meta:
        model = Customer
        exclude = ("business",)
        read_only_fields = ("id", "created_at", "updated_at")

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        exclude = ("business",)
        read_only_fields = ("id", "created_at", "updated_at")

class VariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        exclude = ("business", "product")
        read_only_fields = ("id", "created_at", "updated_at")

class ProductSerializer(serializers.ModelSerializer):
    variants = VariantSerializer(many=True, required=False)
    category_name = serializers.CharField(source="category.name", read_only=True)
    class Meta:
        model = Product
        exclude = ("business",)
        read_only_fields = ("id", "created_at", "updated_at", "slug", "moderation_status")
    def validate_category(self, value):
        if value.business_id != get_membership(self.context["request"].user).business_id:
            raise serializers.ValidationError("La categoría no pertenece a tu empresa.")
        return value
    @transaction.atomic
    def create(self, validated):
        validated.pop("business", None)
        variants = validated.pop("variants", [])
        business = get_membership(self.context["request"].user).business
        if validated.get("is_public"):enforce_plan_limit(business,"public_products",Product.objects.filter(business=business,is_public=True,is_active=True).count())
        base = slugify(validated["name"]) or "producto"; slug = base; suffix = 2
        while Product.objects.filter(business=business, slug=slug).exists(): slug=f"{base}-{suffix}"; suffix += 1
        product = Product.objects.create(business=business, slug=slug, **validated)
        for variant in variants: ProductVariant.objects.create(business=business, product=product, **variant)
        record_audit("product.created",product,actor=self.context["request"].user,request=self.context["request"])
        return product
    @transaction.atomic
    def update(self, instance, validated):
        variants = validated.pop("variants", None)
        if validated.get("is_public") and not instance.is_public:
            enforce_plan_limit(instance.business,"public_products",Product.objects.filter(business=instance.business,is_public=True,is_active=True).exclude(pk=instance.pk).count())
        instance = super().update(instance, validated)
        if variants is not None:
            instance.variants.all().delete()
            for variant in variants: ProductVariant.objects.create(business=instance.business, product=instance, **variant)
        record_audit("product.updated",instance,actor=self.context["request"].user,request=self.context["request"])
        return instance

class OrderItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)
    class Meta:
        model = OrderItem
        exclude = ("business", "order")
        read_only_fields = ("id", "created_at", "updated_at")

class PaymentSerializer(serializers.ModelSerializer):
    registered_by_name = serializers.CharField(source="registered_by.get_full_name", read_only=True)
    class Meta:
        model = Payment
        exclude = ("business", "registered_by")
        read_only_fields = ("id", "created_at", "updated_at", "is_void")
    def validate_order(self, value):
        if value.business_id != get_membership(self.context["request"].user).business_id:
            raise serializers.ValidationError("El pedido no pertenece a tu empresa.")
        return value
    def validate(self, data):
        order=data.get("order")
        amount=data.get("amount")
        if order and amount and amount > order.balance:
            raise serializers.ValidationError({"amount":"El pago no puede superar el saldo pendiente."})
        return data
    @transaction.atomic
    def create(self, validated):
        validated.pop("business", None)
        request = self.context["request"]; business = get_membership(request.user).business
        payment = Payment.objects.create(business=business, registered_by=request.user, **validated)
        recalculate_order(payment.order)
        record_audit("payment.recorded",payment,actor=request.user,request=request,metadata={"amount":str(payment.amount),"order":payment.order.display_number})
        return payment

class StatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source="changed_by.get_full_name", read_only=True)
    class Meta:
        model = OrderStatusHistory
        fields = "__all__"

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    payments = PaymentSerializer(many=True, read_only=True)
    status_history = StatusHistorySerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    responsible_name = serializers.CharField(source="responsible.get_full_name", read_only=True)
    display_number = serializers.CharField(read_only=True)
    class Meta:
        model = Order
        exclude = ("business",)
        read_only_fields = ("id", "number", "public_id", "subtotal", "total", "total_paid", "balance", "payment_status", "created_at", "updated_at")
    def validate(self, data):
        business = get_membership(self.context["request"].user).business
        if not self.instance and not self.initial_data.get("items"):
            raise serializers.ValidationError({"items":"El pedido debe incluir al menos un producto."})
        if data.get("customer") and data["customer"].business_id != business.id: raise serializers.ValidationError({"customer":"El cliente no pertenece a tu empresa."})
        if data.get("responsible") and not data["responsible"].memberships.filter(business=business, is_active=True).exists(): raise serializers.ValidationError({"responsible":"El responsable no pertenece a tu empresa."})
        for item in self.initial_data.get("items", []):
            product_id=item.get("product"); variant_id=item.get("variant")
            if product_id and not Product.objects.filter(id=product_id,business=business,is_active=True).exists(): raise serializers.ValidationError({"items":"Uno de los productos no pertenece a tu empresa."})
            if variant_id and not ProductVariant.objects.filter(id=variant_id,business=business,is_active=True).exists(): raise serializers.ValidationError({"items":"Una variante no pertenece a tu empresa."})
        return data
    @transaction.atomic
    def create(self, validated):
        validated.pop("business", None)
        items = validated.pop("items"); request=self.context["request"]; business=get_membership(request.user).business
        enforce_plan_limit(business,"orders",Order.objects.filter(business=business,created_at__year=timezone.now().year,created_at__month=timezone.now().month).count())
        order=Order.objects.create(business=business,number=next_order_number(business),**validated)
        for item in items: OrderItem.objects.create(business=business,order=order,**item)
        OrderStatusHistory.objects.create(order=order,to_status=order.status,changed_by=request.user,comment="Pedido creado")
        record_audit("order.created",order,actor=request.user,request=request,metadata={"number":order.display_number})
        return recalculate_order(order)
    @transaction.atomic
    def update(self, instance, validated):
        items=validated.pop("items",None); old_status=instance.status
        instance=super().update(instance,validated)
        if items is not None:
            instance.items.all().delete()
            for item in items: OrderItem.objects.create(business=instance.business,order=instance,**item)
        if old_status != instance.status:
            OrderStatusHistory.objects.create(order=instance,from_status=old_status,to_status=instance.status,changed_by=self.context["request"].user)
            record_audit("order.status_changed",instance,actor=self.context["request"].user,request=self.context["request"],metadata={"from":old_status,"to":instance.status})
        return recalculate_order(instance)

class OrderListSerializer(serializers.ModelSerializer):
    customer_name=serializers.CharField(source="customer.full_name",read_only=True)
    customer_whatsapp=serializers.CharField(source="customer.whatsapp",read_only=True)
    customer_phone=serializers.CharField(source="customer.phone",read_only=True)
    display_number=serializers.CharField(read_only=True)
    items_count=serializers.IntegerField(read_only=True)
    class Meta:
        model=Order
        fields=("id","public_id","display_number","customer","customer_name","customer_whatsapp","customer_phone","origin","due_date","status","priority","responsible","subtotal","total","total_paid","balance","payment_status","created_at","items_count")

class PublicProductSerializer(serializers.ModelSerializer):
    variants=VariantSerializer(many=True,read_only=True)
    category_name=serializers.CharField(source="category.name",read_only=True)
    class Meta:
        model=Product
        fields=("id","name","slug","category","category_name","short_description","description","image","sale_price","price_type","minimum_quantity","production_days","techniques","customization_options","variants")

class MarketplaceProductSerializer(PublicProductSerializer):
    business=serializers.SerializerMethodField()
    def get_business(self,obj):
        b=obj.business
        return {"name":b.name,"slug":b.slug,"region":b.region,"commune":b.commune,"is_verified":b.is_verified,"allows_pickup":b.allows_pickup,"local_delivery":b.local_delivery,"national_delivery":b.national_delivery}
    class Meta(PublicProductSerializer.Meta):
        fields=PublicProductSerializer.Meta.fields+("business",)

class PublicOrderRequestSerializer(serializers.Serializer):
    product_slug=serializers.SlugField()
    variant=serializers.IntegerField(required=False,allow_null=True)
    quantity=serializers.IntegerField(min_value=1)
    first_name=serializers.CharField(max_length=100)
    last_name=serializers.CharField(max_length=100,required=False,allow_blank=True)
    email=serializers.EmailField(required=False,allow_blank=True)
    phone=serializers.CharField(max_length=20)
    whatsapp=serializers.CharField(max_length=20,required=False,allow_blank=True)
    region=serializers.CharField(max_length=100,required=False,allow_blank=True)
    commune=serializers.CharField(max_length=100,required=False,allow_blank=True)
    due_date=serializers.DateField(required=False,allow_null=True)
    customizations=serializers.JSONField(required=False)
    notes=serializers.CharField(required=False,allow_blank=True)
    def validate(self,data):
        business=self.context["business"]
        try: product=Product.objects.get(business=business,slug=data["product_slug"],is_active=True,is_public=True)
        except Product.DoesNotExist: raise serializers.ValidationError({"product_slug":"El producto no está disponible."})
        if data["quantity"] < product.minimum_quantity: raise serializers.ValidationError({"quantity":f"La cantidad mínima es {product.minimum_quantity}."})
        variant_id=data.get("variant")
        variant=None
        if variant_id:
            variant=product.variants.filter(id=variant_id,is_active=True).first()
            if not variant: raise serializers.ValidationError({"variant":"La variante no está disponible."})
        data["product_object"]=product;data["variant_object"]=variant
        return data
    @transaction.atomic
    def create(self,data):
        business=self.context["business"];product=data.pop("product_object");variant=data.pop("variant_object");data.pop("product_slug");quantity=data.pop("quantity");customizations=data.pop("customizations",{});notes=data.pop("notes","");due_date=data.pop("due_date",None)
        now=timezone.now();enforce_plan_limit(business,"orders",Order.objects.filter(business=business,created_at__year=now.year,created_at__month=now.month).count())
        phone=data["phone"];customer=Customer.objects.filter(business=business,phone=phone).first()
        if customer:
            for field,value in data.items():
                if value:setattr(customer,field,value)
            customer.save()
        else:customer=Customer.objects.create(business=business,**data)
        unit_price=product.sale_price+(variant.price_adjustment if variant else 0)
        order=Order.objects.create(business=business,number=next_order_number(business),customer=customer,origin=Order.Origin.PUBLIC_STORE,due_date=due_date,customer_instructions=notes)
        OrderItem.objects.create(business=business,order=order,product=product,variant=variant,description=product.name,quantity=quantity,unit_cost=product.internal_cost,unit_price=unit_price,customizations=customizations,notes=notes)
        recalculate_order(order)
        record_audit("order.public_requested",order,metadata={"number":order.display_number})
        return order

class QuoteRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model=QuoteRequest
        fields=("title","category","product_type","description","quantity","specifications","approximate_budget","required_date","region","commune","delivery_method","delivery_scope","contact_name","contact_email","contact_phone","contact_whatsapp")
    @transaction.atomic
    def create(self,validated):
        quote=QuoteRequest.objects.create(**validated);match_quote_request(quote);return quote

class QuoteRequestBusinessSerializer(serializers.ModelSerializer):
    match_score=serializers.IntegerField(read_only=True)
    class Meta:
        model=QuoteRequest
        fields=("id","public_id","title","category","product_type","description","quantity","specifications","approximate_budget","required_date","region","commune","delivery_method","delivery_scope","status","created_at","match_score")

class QuoteProposalSerializer(serializers.ModelSerializer):
    business_name=serializers.CharField(source="business.name",read_only=True)
    request_title=serializers.CharField(source="request.title",read_only=True)
    class Meta:
        model=QuoteProposal
        exclude=("business","created_by")
        read_only_fields=("id","public_id","created_at","updated_at")
    def validate_request(self,value):
        business=get_membership(self.context["request"].user).business
        if not value.matches.filter(business=business,is_active=True).exists():raise serializers.ValidationError("Esta solicitud no fue asignada a tu empresa.")
        return value
    def validate(self,data):
        if data.get("deposit_percentage",0)>100:raise serializers.ValidationError({"deposit_percentage":"No puede superar 100%."})
        if data.get("valid_until") and data["valid_until"]<timezone.localdate():raise serializers.ValidationError({"valid_until":"La vigencia debe terminar en el futuro."})
        quote=data.get("request");unit=data.get("unit_price",0);discount=data.get("discount",0);shipping=data.get("shipping_cost",0);total=data.get("total_price",0)
        if quote and unit and unit*quote.quantity-discount+shipping!=total:raise serializers.ValidationError({"total_price":"El total debe coincidir con cantidad × precio unitario − descuento + despacho."})
        return data
    def create(self,validated):
        request=self.context["request"];business=get_membership(request.user).business
        now=timezone.now();enforce_plan_limit(business,"quote_responses",QuoteProposal.objects.filter(business=business,created_at__year=now.year,created_at__month=now.month).count())
        proposal=QuoteProposal.objects.create(business=business,created_by=request.user,**validated)
        Conversation.objects.create(proposal=proposal)
        if proposal.status=="sent" and proposal.request.status=="open":proposal.request.status="proposals";proposal.request.save(update_fields=["status"])
        record_audit("quote.proposal_sent",proposal,business=business,actor=request.user,request=request,metadata={"total":str(proposal.total_price)})
        return proposal

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model=Message
        fields=("id","sender_type","body","is_read","created_at")
        read_only_fields=("id","sender_type","is_read","created_at")

class PublicProposalSerializer(serializers.ModelSerializer):
    business=serializers.SerializerMethodField()
    messages=serializers.SerializerMethodField()
    def get_business(self,obj):return {"name":obj.business.name,"slug":obj.business.slug,"is_verified":obj.business.is_verified,"region":obj.business.region}
    def get_messages(self,obj):return MessageSerializer(obj.conversation.messages.all(),many=True).data if hasattr(obj,"conversation") else []
    class Meta:
        model=QuoteProposal
        fields=("public_id","business","total_price","unit_price","discount","shipping_cost","production_days","estimated_delivery","materials","technique","payment_terms","deposit_percentage","valid_until","comments","status","messages","created_at")

class OrderFileSerializer(serializers.ModelSerializer):
    download_url=serializers.SerializerMethodField()
    class Meta:
        model=OrderFile
        fields=("id","order","item","kind","original_name","mime_type","size","download_url","created_at")
        read_only_fields=("id","original_name","mime_type","size","download_url","created_at")
    def get_download_url(self,obj):return f"/api/v1/order-files/{obj.id}/download/"

class DesignApprovalSerializer(serializers.ModelSerializer):
    url=serializers.SerializerMethodField();is_available=serializers.BooleanField(read_only=True)
    class Meta:
        model=DesignApproval
        fields=("id","order","token","expires_at","revoked_at","approved_at","approved_by_name","comment","created_at","is_available","url")
        read_only_fields=("id","token","revoked_at","approved_at","approved_by_name","comment","created_at","is_available","url")
    def get_url(self,obj):return f"/aprobar/{obj.token}"
