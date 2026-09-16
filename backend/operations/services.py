from decimal import Decimal
from django.db import transaction
from django.conf import settings
from django.core.mail import send_mail
from django.utils.html import escape
from django.db.models import Sum
from businesses.models import BusinessSetting
from businesses.models import Business
from .models import AuditLog,Notification,Product,QuoteMatch
from rest_framework.exceptions import ValidationError

def send_event_email(subject,body,recipients,action_url=""):
    recipients=[email for email in recipients if email]
    if not recipients:return
    full_body=f"{body}\n\n{action_url}" if action_url else body
    safe_subject=escape(subject);safe_body=escape(body);safe_url=escape(action_url)
    html=f"<div style='font-family:Arial,sans-serif;max-width:600px'><h2 style='color:#5b4cf0'>{safe_subject}</h2><p>{safe_body}</p>"+(f"<p><a href='{safe_url}' style='background:#5b4cf0;color:white;padding:12px 18px;border-radius:8px;text-decoration:none'>Abrir EstampaFlow</a></p>" if action_url else "")+"<p style='color:#777'>Tus pedidos personalizados, bajo control.</p></div>"
    def deliver():
        try:send_mail(subject,full_body,settings.DEFAULT_FROM_EMAIL,recipients,html_message=html,fail_silently=False)
        except Exception:pass
    transaction.on_commit(deliver)

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
    matches=[QuoteMatch.objects.create(request=quote,business=business,score=score,reasons=reasons) for score,business,reasons in ranked[:max_matches]]
    for match in matches:notify_business(match.business,"quote.available","Nueva solicitud compatible",quote.title,"/app/cotizaciones")
    return matches

def enforce_plan_limit(business,key,current):
    try:limit=business.subscription.limit(key)
    except Exception:return
    if limit is not None and current>=int(limit):raise ValidationError({"plan":f"Alcanzaste el límite de {key} de tu plan."})

def record_audit(action,entity,business=None,actor=None,request=None,metadata=None):
    if business is None:business=getattr(entity,"business",None)
    ip=request.META.get("REMOTE_ADDR") if request else None
    return AuditLog.objects.create(business=business,actor=actor,action=action,entity_type=entity.__class__.__name__,entity_id=str(getattr(entity,"pk","")),metadata=metadata or {},ip_address=ip)

def notify_business(business,kind,title,body="",url=""):
    recipients=business.memberships.filter(is_active=True).select_related("user")
    active=[membership for membership in recipients if membership.user.is_active]
    notifications=[Notification.objects.create(business=business,recipient=membership.user,kind=kind,title=title,body=body,url=url) for membership in active]
    send_event_email(title,body,[membership.user.email for membership in active],f"{settings.FRONTEND_URL}{url}" if url else settings.FRONTEND_URL)
    return notifications
