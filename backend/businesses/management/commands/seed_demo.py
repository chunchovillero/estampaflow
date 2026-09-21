from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.test.utils import override_settings
from django.utils import timezone
from django.utils.text import slugify

from businesses.models import Business, BusinessMembership, BusinessSetting, Plan, Subscription
from operations.models import (Conversation, Customer, FeaturedBusiness, FeaturedProduct, Message,
    Notification, Order, OrderItem, OrderStatusHistory, Payment, Product, ProductCategory,
    ProductVariant, QuoteProposal, QuoteRequest)
from operations.services import match_quote_request, recalculate_order

BUSINESSES = [
    ("Estampados Aurora", "aurora", "aurora@demo.cl", "Metropolitana de Santiago", "Santiago"),
    ("Tinta Sur", "tinta-sur", "tintasur@demo.cl", "Biobío", "Concepción"),
    ("Color Norte", "color-norte", "colornorte@demo.cl", "Antofagasta", "Antofagasta"),
]
PRODUCTS = [
    ("Polera personalizada DTF", "Poleras", 12990, 5500, "DTF"),
    ("Polera corporativa", "Productos para empresas", 10990, 4300, "Serigrafía"),
    ("Polerón bordado", "Polerones", 29990, 14500, "Bordado"),
    ("Tazón mágico", "Tazones", 8990, 3200, "Sublimación"),
    ("Tazón con fotografía", "Regalos con fotografías", 6990, 2400, "Sublimación"),
    ("Pack de stickers", "Stickers", 14990, 5200, "Impresión UV"),
    ("Chapitas para eventos", "Chapitas", 990, 300, "Impresión digital"),
    ("Llavero acrílico", "Llaveros", 3990, 1300, "Impresión UV"),
    ("Camiseta deportiva", "Ropa deportiva", 18990, 8900, "Sublimación"),
    ("Set de cumpleaños", "Cumpleaños y eventos", 24990, 10500, "Impresión digital"),
    ("Gorro corporativo", "Productos para empresas", 9990, 4100, "Bordado"),
    ("Delantal personalizado", "Productos para empresas", 15990, 6800, "DTF"),
]
NAMES = ["Camila", "Matías", "Sofía", "Benjamín", "Valentina", "Tomás", "Martina", "Vicente", "Fernanda", "Diego", "Antonia", "Joaquín"]
SURNAMES = ["Soto", "Muñoz", "Rojas", "Contreras", "Sepúlveda", "Silva", "Martínez", "Pérez", "González", "Araya"]


class Command(BaseCommand):
    help = "Crea un conjunto amplio y repetible de datos de demostración"

    def add_arguments(self, parser):
        parser.add_argument("--customers", type=int, default=30, help="Clientes por empresa")
        parser.add_argument("--products", type=int, default=18, help="Productos por empresa")
        parser.add_argument("--orders", type=int, default=60, help="Pedidos por empresa")
        parser.add_argument("--quotes", type=int, default=20, help="Solicitudes generales")

    @transaction.atomic
    def handle(self, *args, **options):
        amount = {key: max(1, options[key]) for key in ("customers", "products", "orders", "quotes")}
        User, now, today = get_user_model(), timezone.now(), timezone.localdate()
        admin, _ = User.objects.get_or_create(username="admin@estampaflow.local", defaults={"email": "admin@estampaflow.local", "first_name": "Admin"})
        admin.is_staff = admin.is_superuser = admin.email_verified = True
        admin.set_password("Demo-Admin-2026"); admin.save()
        plans = []
        for code, name, price, limits in [
            ("professional", "Profesional", 39990, {"orders": 500, "public_products": 200, "users": 15, "storage_mb": 10000, "quote_responses": 100}),
            ("entrepreneur", "Emprendedor", 19990, {"orders": 150, "public_products": 40, "users": 5, "storage_mb": 2000, "quote_responses": 30}),
            ("free", "Gratis", 0, {"orders": 30, "public_products": 5, "users": 2, "storage_mb": 100, "quote_responses": 3}),
        ]:
            plan, _ = Plan.objects.update_or_create(code=code, defaults={"name": name, "monthly_price": price, "limits": limits})
            plans.append(plan)

        demo_businesses = []
        for bidx, (name, slug, email, region, commune) in enumerate(BUSINESSES):
            business, _ = Business.objects.update_or_create(slug=slug, defaults={
                "name": name, "email": email, "phone": f"+5697000000{bidx}", "whatsapp": f"+5697000000{bidx}",
                "instagram": f"@{slug.replace('-', '')}", "description": "Productos personalizados hechos con dedicación en Chile.",
                "address": f"Avenida Creativa {120+bidx}", "region": region, "commune": commune,
                "coverage": "Retiro local y envíos a todo Chile", "status": "active", "is_verified": True,
                "is_public": True, "local_delivery": True, "national_delivery": True, "weekly_capacity": 250,
            })
            demo_businesses.append(business)
            Subscription.objects.update_or_create(business=business, defaults={"plan": plans[bidx], "status": "active"})
            setting, _ = BusinessSetting.objects.get_or_create(business=business)
            setting.whatsapp_templates = {"summary": "Hola {cliente}, resumen {pedido}: {total}.", "approval": "Tu diseño {pedido} está listo.", "production": "Tu pedido {pedido} entró en producción.", "ready": "Tu pedido {pedido} está listo.", "balance": "Saldo de {pedido}: {saldo}."}
            setting.payment_methods = ["Transferencia", "Efectivo", "Débito", "Crédito"]
            setting.delivery_methods = ["Retiro", "Despacho local", "Envío nacional"]
            setting.save()

            users = []
            for role, user_email, first, password in [("owner", email, "Propietario", "Demo-Owner-2026"), ("collaborator", f"equipo@{slug}.demo.cl", "Daniela", "Demo-Team-2026")]:
                user, _ = User.objects.get_or_create(username=user_email, defaults={"email": user_email, "first_name": first})
                user.email_verified = True; user.set_password(password); user.save()
                BusinessMembership.objects.update_or_create(business=business, user=user, defaults={"role": role, "is_active": True})
                users.append(user)

            categories = {row[1]: ProductCategory.objects.get_or_create(business=business, name=row[1])[0] for row in PRODUCTS}
            products = []
            for pidx in range(amount["products"]):
                base, category, price, cost, technique = PRODUCTS[pidx % len(PRODUCTS)]
                edition = pidx // len(PRODUCTS)
                product_name = base if not edition else f"{base} · Edición {edition+1}"
                product, _ = Product.objects.update_or_create(business=business, slug=slugify(product_name), defaults={
                    "category": categories[category], "name": product_name, "short_description": f"{product_name} con personalización incluida.",
                    "description": "Personaliza colores, textos, fotografías y ubicación del diseño.", "internal_cost": cost,
                    "sale_price": price + edition*1000, "price_type": "from" if pidx % 4 == 0 else "fixed",
                    "minimum_quantity": 10 if category in {"Chapitas", "Stickers"} else 1, "production_days": 2+pidx % 8,
                    "is_active": True, "is_public": pidx < max(5, amount["products"]-3),
                    "moderation_status": "pending" if pidx % 7 == 0 else "approved", "track_stock": pidx % 3 == 0,
                    "stock": 15+pidx*3, "techniques": [technique], "customization_options": ["Texto", "Color", "Archivo", "Indicaciones"],
                })
                products.append(product)
                for vidx, (size, color) in enumerate((("S", "Negro"), ("M", "Blanco"), ("L", "Morado"))):
                    ProductVariant.objects.update_or_create(business=business, product=product, name=f"{color} / {size}", defaults={"attributes": {"color": color, "talla": size}, "sku": f"{slug[:3].upper()}-{pidx+1:02d}-{vidx+1}", "stock": 10+vidx*5, "is_active": True})
            FeaturedBusiness.objects.update_or_create(business=business, defaults={"position": bidx+1, "reason": "Empresa demo", "is_active": True})
            for fidx, product in enumerate(products[:3]):
                FeaturedProduct.objects.update_or_create(product=product, defaults={"position": bidx*3+fidx+1, "reason": "Producto demo", "is_active": True})

            customers = []
            for cidx in range(amount["customers"]):
                first, last, phone = NAMES[(cidx+bidx) % len(NAMES)], SURNAMES[(cidx*2+bidx) % len(SURNAMES)], f"+569{bidx+1}{cidx:07d}"
                customer, _ = Customer.objects.update_or_create(business=business, email=f"cliente{cidx+1}@{slug}.demo.cl", defaults={"first_name": first, "last_name": last, "phone": phone, "whatsapp": phone, "instagram": f"@{slugify(first+last).replace('-', '')}{cidx+1}", "address": f"Calle Demo {100+cidx}", "region": region, "commune": commune, "notes": "Cliente frecuente" if cidx % 5 == 0 else ""})
                customers.append(customer)

            for oidx in range(amount["orders"]):
                status = Order.Status.values[oidx % len(Order.Status.values)]
                order, created = Order.objects.get_or_create(business=business, number=oidx+1, defaults={
                    "customer": customers[oidx % len(customers)], "origin": Order.Origin.values[oidx % len(Order.Origin.values)],
                    "due_date": today+timedelta(days=(oidx % 24)-8), "status": status,
                    "priority": Order.Priority.values[oidx % len(Order.Priority.values)], "responsible": users[oidx % 2],
                    "discount": 2000 if oidx % 6 == 0 else 0, "shipping_cost": 3990 if oidx % 3 else 0,
                    "delivery_method": "shipping" if oidx % 3 else "pickup", "delivery_address": customers[oidx % len(customers)].address,
                    "customer_instructions": "Confirmar colores antes de producir.", "internal_notes": "Dato demo.",
                    "delivered_at": now-timedelta(days=2) if status == Order.Status.DELIVERED else None,
                })
                if created:
                    for iidx in range(1+oidx % 3):
                        product = products[(oidx+iidx) % len(products)]; variant = product.variants.all()[iidx % 3]
                        OrderItem.objects.create(business=business, order=order, product=product, variant=variant, description=product.name, quantity=1+(oidx+iidx) % 12, unit_cost=product.internal_cost, unit_price=product.sale_price, customizations={"nombre": order.customer.first_name, **variant.attributes}, notes="Usar referencia del cliente.")
                    recalculate_order(order)
                    if status != Order.Status.CANCELLED and oidx % 4:
                        ratio = Decimal("1") if status in {Order.Status.DELIVERED, Order.Status.READY} else Decimal("0.5")
                        Payment.objects.create(business=business, order=order, amount=max(1, (order.total*ratio).quantize(Decimal("1"))), paid_at=now-timedelta(days=oidx % 60), method=Payment.Method.values[oidx % len(Payment.Method.values)], reference=f"DEMO-{bidx+1}-{oidx+1:04d}", registered_by=users[0])
                        recalculate_order(order)
                    OrderStatusHistory.objects.create(order=order, to_status=status, changed_by=users[0], comment="Estado inicial demo")
                    Order.objects.filter(pk=order.pk).update(created_at=now-timedelta(days=oidx % 75))
            setting.next_order_number = max(setting.next_order_number, amount["orders"]+1); setting.save(update_fields=["next_order_number"])
            for nidx in range(12):
                Notification.objects.get_or_create(business=business, recipient=users[0], kind="demo", title=f"Actividad de demostración {nidx+1}", defaults={"body": "Tienes novedades en pedidos y cotizaciones.", "url": "/app/pedidos", "read_at": now if nidx % 3 == 0 else None})

        quote_categories = ["Poleras", "Tazones", "Stickers", "Productos para empresas", "Ropa deportiva"]
        for qidx in range(amount["quotes"]):
            category, quantity = quote_categories[qidx % 5], 10+qidx*5
            quote, created = QuoteRequest.objects.get_or_create(contact_email=f"cotizacion{qidx+1}@demo.cl", title=f"{quantity} {category.lower()} personalizadas", defaults={"category": category, "product_type": category, "description": "Productos personalizados con logo y colores corporativos.", "quantity": quantity, "specifications": {"tallas": "S, M, L y XL", "colores": "A elección"}, "approximate_budget": 120000+qidx*45000, "required_date": today+timedelta(days=12+qidx), "region": BUSINESSES[qidx % 3][3], "commune": BUSINESSES[qidx % 3][4], "delivery_method": "shipping" if qidx % 2 else "pickup", "contact_name": f"{NAMES[qidx % len(NAMES)]} {SURNAMES[qidx % len(SURNAMES)]}", "contact_phone": f"+5698{qidx:07d}", "contact_whatsapp": f"+5698{qidx:07d}"})
            if created:
                with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
                    match_quote_request(quote)
            for pidx, business in enumerate(demo_businesses[:1+qidx % 3]):
                owner = business.memberships.filter(role="owner").first().user; unit = Decimal(6500+pidx*750+qidx*100)
                proposal, _ = QuoteProposal.objects.get_or_create(request=quote, business=business, defaults={"total_price": unit*quantity+3990, "unit_price": unit, "discount": 5000 if quantity >= 50 else 0, "shipping_cost": 3990, "production_days": 4+pidx*2, "estimated_delivery": today+timedelta(days=9+pidx*2), "materials": "Material premium", "technique": "DTF y sublimación", "payment_terms": "50% de abono y saldo contra entrega", "deposit_percentage": 50, "valid_until": today+timedelta(days=7), "comments": "Incluye diseño y una ronda de cambios.", "status": "viewed" if qidx % 3 == 0 else "sent", "created_by": owner})
                conversation, _ = Conversation.objects.get_or_create(proposal=proposal)
                Message.objects.get_or_create(conversation=conversation, sender_type="business", body="Podemos realizar el trabajo dentro del plazo.", defaults={"sender_user": owner, "is_read": qidx % 2 == 0})
                Message.objects.get_or_create(conversation=conversation, sender_type="client", body="¿Incluye una muestra digital antes de producir?")
            if quote.proposals.exists() and quote.status == "open": quote.status = "proposals"; quote.save(update_fields=["status"])

        self.stdout.write(self.style.SUCCESS(f"Datos demo listos: 3 empresas, {amount['customers']*3} clientes, {amount['products']*3} productos, {amount['orders']*3} pedidos y {amount['quotes']} cotizaciones."))
