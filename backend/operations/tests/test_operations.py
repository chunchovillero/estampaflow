from datetime import timedelta
from decimal import Decimal
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from businesses.models import Business,BusinessMembership,Plan,Subscription
from operations.models import AuditLog,Customer,Order,Payment,Product,ProductCategory

pytestmark=pytest.mark.django_db
User=get_user_model()

def tenant(name,email,role="owner"):
    business=Business.objects.create(name=name,status="active")
    user=User.objects.create_user(username=email,email=email,password="Marea-Violeta-4821")
    BusinessMembership.objects.create(business=business,user=user,role=role)
    client=APIClient();client.force_authenticate(user)
    return business,user,client

def catalog(business):
    category=ProductCategory.objects.create(business=business,name="Poleras")
    product=Product.objects.create(business=business,category=category,name="Polera DTF",slug="polera-dtf",sale_price=10000)
    customer=Customer.objects.create(business=business,first_name="Camila",phone="+56912345678")
    return category,product,customer

def order_payload(customer,product,price="10000",quantity=2):
    return {"customer":customer.id,"status":"new","priority":"normal","origin":"manual","discount":"1000","shipping_cost":"2000","items":[{"product":product.id,"description":"Polera personalizada","quantity":quantity,"unit_cost":"5000","unit_price":price,"customizations":{"talla":"M","color":"Negro"}}]}

def test_customer_and_product_are_assigned_to_authenticated_business():
    business,_,client=tenant("Aurora","owner@aurora.cl")
    customer=client.post("/api/v1/customers/",{"first_name":"Ana","phone":"+56911111111"},format="json")
    assert customer.status_code==201
    assert Customer.objects.get(id=customer.data["id"]).business==business

def test_lists_never_expose_other_tenant_data():
    first,_,client=tenant("Aurora","owner@aurora.cl");second,_,_=tenant("Sur","owner@sur.cl")
    Customer.objects.create(business=first,first_name="Visible",phone="1")
    Customer.objects.create(business=second,first_name="Privado",phone="2")
    data=client.get("/api/v1/customers/").data["results"]
    assert [item["first_name"] for item in data]==["Visible"]

def test_order_calculates_totals_and_sequential_number():
    business,_,client=tenant("Aurora","owner@aurora.cl");_,product,customer=catalog(business)
    first=client.post("/api/v1/orders/",order_payload(customer,product),format="json")
    second=client.post("/api/v1/orders/",order_payload(customer,product,"5000",1),format="json")
    assert first.status_code==201 and first.data["number"]==1 and Decimal(first.data["total"])==Decimal("21000")
    assert second.data["number"]==2

def test_order_rejects_customer_and_product_from_other_business():
    business,_,client=tenant("Aurora","owner@aurora.cl");_,product,_=catalog(business)
    other,_,_=tenant("Sur","owner@sur.cl");_,foreign_product,foreign_customer=catalog(other)
    assert client.post("/api/v1/orders/",order_payload(foreign_customer,product),format="json").status_code==400
    own_customer=Customer.objects.filter(business=business).first()
    assert client.post("/api/v1/orders/",order_payload(own_customer,foreign_product),format="json").status_code==400

def test_payment_updates_paid_amount_balance_and_status():
    business,_,client=tenant("Aurora","owner@aurora.cl");_,product,customer=catalog(business)
    order_id=client.post("/api/v1/orders/",order_payload(customer,product),format="json").data["id"]
    response=client.post("/api/v1/payments/",{"order":order_id,"amount":"5000","paid_at":timezone.now().isoformat(),"method":"transfer"},format="json")
    order=Order.objects.get(id=order_id)
    assert response.status_code==201 and order.total_paid==5000 and order.balance==16000 and order.payment_status=="partial"
    assert AuditLog.objects.filter(action="payment.recorded",business=business,entity_id=str(response.data["id"])).exists()

def test_payment_cannot_exceed_pending_balance():
    business,_,client=tenant("Aurora","owner@aurora.cl");_,product,customer=catalog(business)
    order_id=client.post("/api/v1/orders/",order_payload(customer,product),format="json").data["id"]
    response=client.post("/api/v1/payments/",{"order":order_id,"amount":"99999","paid_at":timezone.now().isoformat(),"method":"cash"},format="json")
    assert response.status_code==400 and Payment.objects.count()==0

def test_order_requires_at_least_one_item():
    business,_,client=tenant("Aurora","owner@aurora.cl");_,_,customer=catalog(business)
    assert client.post("/api/v1/orders/",{"customer":customer.id,"items":[]},format="json").status_code==400

def test_status_change_keeps_history():
    business,_,client=tenant("Aurora","owner@aurora.cl");_,product,customer=catalog(business)
    order_id=client.post("/api/v1/orders/",order_payload(customer,product),format="json").data["id"]
    response=client.post(f"/api/v1/orders/{order_id}/change_status/",{"status":"production"},format="json")
    order=Order.objects.get(id=order_id)
    assert response.status_code==200 and order.status=="production"
    assert order.status_history.filter(from_status="new",to_status="production").exists()

def test_dashboard_counts_overdue_orders():
    business,user,client=tenant("Aurora","owner@aurora.cl");_,product,customer=catalog(business)
    order=Order.objects.create(business=business,number=1,customer=customer,due_date=timezone.localdate()-timedelta(days=1))
    assert client.get("/api/v1/dashboard/").data["overdue"]==1

def test_monthly_order_limit_is_enforced():
    business,_,client=tenant("Aurora","limit@aurora.cl");_,product,customer=catalog(business)
    plan=Plan.objects.create(code="no-orders",name="Sin pedidos",limits={"orders":0})
    Subscription.objects.create(business=business,plan=plan)
    response=client.post("/api/v1/orders/",order_payload(customer,product),format="json")
    assert response.status_code==400 and Order.objects.filter(business=business).count()==0
