from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from businesses.models import BusinessSetting
from businesses.models import Business
from .models import Product,QuoteMatch
from rest_framework.exceptions import ValidationError

def next_order_number(business):
    setting, _ = BusinessSetting.objects.get_or_create(business=business)
    setting = BusinessSetting.objects.select_for_update().get(pk=setting.pk)
    number = setting.next_order_number
    setting.next_order_number += 1
    setting.save(update_fields=["next_order_number"])
    return number

def recalculate_order(order):
    subtotal = sum((item.line_total for item in order.items.all()), Decimal("0"))
    paid = order.payments.filter(is_void=False).aggregate(value=Sum("amount"))["value"] or Decimal("0")
    order.subtotal = subtotal
    order.total = max(Decimal("0"), subtotal - order.discount + order.shipping_cost)
    order.total_paid = paid
    order.balance = max(Decimal("0"), order.total - paid)
    order.payment_status = "paid" if order.total and order.balance == 0 else ("partial" if paid else "pending")
    order.save(update_fields=["subtotal", "total", "total_paid", "balance", "payment_status", "updated_at"])
    return order

def match_quote_request(quote,max_matches=5):
    candidates=Business.objects.filter(status="active",is_verified=True,accepts_quotes=True,is_public=True)
    ranked=[]
    for business in candidates:
        products=Product.objects.filter(business=business,is_active=True)
        score=0;reasons=[]
        if products.filter(category__name__iexact=quote.category).exists():score+=50;reasons.append("Categoría compatible")
        if quote.product_type and products.filter(name__icontains=quote.product_type).exists():score+=25;reasons.append("Producto compatible")
        if business.region.lower()==quote.region.lower():score+=20;reasons.append("Misma región")
        if quote.delivery_method=="shipping" and business.national_delivery:score+=15;reasons.append("Despacho nacional")
        if quote.delivery_method=="pickup" and business.allows_pickup and business.region.lower()==quote.region.lower():score+=15;reasons.append("Retiro disponible")
        if business.weekly_capacity>=quote.quantity:score+=10;reasons.append("Capacidad disponible")
        if score>=50:ranked.append((score,business,reasons))
    ranked.sort(key=lambda item:(-item[0],item[1].id))
    return [QuoteMatch.objects.create(request=quote,business=business,score=score,reasons=reasons) for score,business,reasons in ranked[:max_matches]]

def enforce_plan_limit(business,key,current):
    try:limit=business.subscription.limit(key)
    except Exception:return
    if limit is not None and current>=int(limit):raise ValidationError({"plan":f"Alcanzaste el límite de {key} de tu plan."})
