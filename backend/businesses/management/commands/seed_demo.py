from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from businesses.models import Business, BusinessMembership, BusinessSetting, Plan, Subscription
from operations.models import Conversation,Customer,FeaturedBusiness,FeaturedProduct,Order,OrderItem,Payment,Product,ProductCategory,ProductVariant,QuoteProposal,QuoteRequest
from operations.services import match_quote_request,recalculate_order

class Command(BaseCommand):
    help = "Crea cuentas y empresas de demostración para desarrollo"
    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        superuser, _ = User.objects.get_or_create(username="admin@estampaflow.local", defaults={"email":"admin@estampaflow.local", "first_name":"Admin", "is_staff":True, "is_superuser":True})
        superuser.set_password("Demo-Admin-2026"); superuser.save()
        free, _ = Plan.objects.get_or_create(code="free", defaults={"name":"Gratis","limits":{"orders":30,"public_products":5,"users":2,"storage_mb":100,"quote_responses":3}})
        Plan.objects.get_or_create(code="entrepreneur", defaults={"name":"Emprendedor","monthly_price":19990,"limits":{"orders":150,"public_products":40,"users":5,"storage_mb":2000,"quote_responses":30},"position":1})
        Plan.objects.get_or_create(code="professional", defaults={"name":"Profesional","monthly_price":39990,"limits":{"orders":500,"public_products":200,"users":15,"storage_mb":10000,"quote_responses":100},"position":2})
        demos = [("Estampados Aurora", "aurora", "aurora@demo.cl"), ("Tinta Sur", "tinta-sur", "tintasur@demo.cl"), ("Color Norte", "color-norte", "colornorte@demo.cl")]
        for name, slug, email in demos:
            business, _ = Business.objects.get_or_create(slug=slug, defaults={"name":name, "email":email, "status":"active", "is_verified":True})
            business.is_public = True
            business.status = "active"
            business.description = "Productos personalizados hechos con dedicación en Chile."
            business.save(update_fields=["is_public", "status", "description"])
            Subscription.objects.get_or_create(business=business,defaults={"plan":free})
            setting, _ = BusinessSetting.objects.get_or_create(business=business)
            if not setting.whatsapp_templates:
                setting.whatsapp_templates={"summary":"Hola {cliente}, este es el resumen de tu pedido {pedido} por {total}.","approval":"Hola {cliente}, tu diseño del pedido {pedido} está listo para revisión.","production":"Hola {cliente}, tu pedido {pedido} entró en producción.","ready":"¡Hola {cliente}! Tu pedido {pedido} está listo.","balance":"Hola {cliente}, te recordamos que el saldo de tu pedido {pedido} es {saldo}."}
                setting.save(update_fields=["whatsapp_templates"])
            owner, _ = User.objects.get_or_create(username=email, defaults={"email":email, "first_name":"Propietario"})
            owner.set_password("Demo-Owner-2026"); owner.save()
            BusinessMembership.objects.get_or_create(business=business, user=owner, defaults={"role":"owner"})
            collaborator_email = f"equipo@{slug}.demo.cl"
            collaborator, _ = User.objects.get_or_create(username=collaborator_email, defaults={"email":collaborator_email, "first_name":"Colaborador"})
            collaborator.set_password("Demo-Team-2026"); collaborator.save()
            BusinessMembership.objects.get_or_create(business=business, user=collaborator, defaults={"role":"collaborator"})
            category, _ = ProductCategory.objects.get_or_create(business=business, name="Poleras")
            product, _ = Product.objects.get_or_create(business=business, slug="polera-dtf", defaults={"category":category,"name":"Polera personalizada DTF","short_description":"Polera de algodón con estampado personalizado","internal_cost":5500,"sale_price":12990,"production_days":3,"techniques":["DTF"]})
            product.is_public = True
            product.moderation_status = "approved"
            product.save(update_fields=["is_public", "moderation_status"])
            FeaturedBusiness.objects.get_or_create(business=business, defaults={"position":demos.index((name, slug, email))+1,"reason":"Emprendimiento demo"})
            FeaturedProduct.objects.get_or_create(product=product, defaults={"position":demos.index((name, slug, email))+1,"reason":"Producto demo"})
            ProductVariant.objects.get_or_create(business=business, product=product, name="Negro / M", defaults={"attributes":{"color":"Negro","talla":"M"},"sku":"POL-NEG-M","stock":20,"is_active":True})
            customer, _ = Customer.objects.get_or_create(business=business, phone="+56912345678", defaults={"first_name":"Camila","last_name":"Soto","whatsapp":"+56912345678","email":f"cliente@{slug}.demo.cl","region":"Metropolitana de Santiago","commune":"Santiago"})
            order, created = Order.objects.get_or_create(business=business, number=1, defaults={"customer":customer,"due_date":timezone.localdate()+timedelta(days=3),"status":"production","priority":"high","responsible":owner,"shipping_cost":3000})
            if created:
                OrderItem.objects.create(business=business, order=order, product=product, description=product.name, quantity=2, unit_cost=5500, unit_price=12990, customizations={"nombre":"Camila","talla":"M","color":"Negro"})
                recalculate_order(order)
                Payment.objects.create(business=business, order=order, amount=10000, paid_at=timezone.now(), method="transfer", reference="DEMO-001", registered_by=owner)
                recalculate_order(order)
            if setting.next_order_number <= 1:
                setting.next_order_number = 2
                setting.save(update_fields=["next_order_number"])
        quote, created = QuoteRequest.objects.get_or_create(title="30 poleras para club deportivo", contact_email="camila.cotiza@demo.cl", defaults={"category":"Poleras","product_type":"Polera deportiva","description":"Poleras negras con logo frontal y número en la espalda.","quantity":30,"specifications":{"tallas":"S, M, L y XL","colores":"Negro y morado","tecnica":"DTF"},"approximate_budget":400000,"required_date":timezone.localdate()+timedelta(days=20),"region":"Metropolitana de Santiago","commune":"Santiago","delivery_method":"shipping","contact_name":"Camila Soto","contact_phone":"+56987654321","contact_whatsapp":"+56987654321"})
        if created: match_quote_request(quote)
        for index, business in enumerate(Business.objects.filter(slug__in=["aurora","tinta-sur"]).order_by("slug")):
            owner=business.memberships.filter(role="owner").first().user
            unit_price=12000-index*500
            proposal, _ = QuoteProposal.objects.get_or_create(request=quote,business=business,defaults={"total_price":unit_price*30-10000+5000,"unit_price":unit_price,"discount":10000,"shipping_cost":5000,"production_days":7+index,"estimated_delivery":timezone.localdate()+timedelta(days=12+index),"technique":"DTF","materials":"Algodón peinado","payment_terms":"50% de abono y saldo contra entrega","deposit_percentage":50,"valid_until":timezone.localdate()+timedelta(days=7),"comments":"Incluye preparación de diseño y una ronda de cambios.","status":"sent","created_by":owner})
            Conversation.objects.get_or_create(proposal=proposal)
        if quote.proposals.exists() and quote.status == "open":
            quote.status = "proposals"
            quote.save(update_fields=["status"])
        self.stdout.write(self.style.SUCCESS("Datos base de demostración creados."))
