import pytest
from rest_framework.test import APIClient
from businesses.models import Business
from operations.models import Customer,Order,Product,ProductCategory

pytestmark=pytest.mark.django_db

def store(slug="aurora",public=True):
    business=Business.objects.create(name="Aurora",slug=slug,status="active",is_public=public)
    category=ProductCategory.objects.create(business=business,name="Poleras")
    product=Product.objects.create(business=business,category=category,name="Polera DTF",slug="polera-dtf",internal_cost=5000,sale_price=12000,is_public=True,minimum_quantity=2)
    return business,product

def test_public_store_only_returns_explicitly_published_products():
    business,product=store();Product.objects.create(business=business,category=product.category,name="Privado",slug="privado",sale_price=1,is_public=False)
    response=APIClient().get("/api/v1/public/stores/aurora/")
    assert response.status_code==200
    assert [item["name"] for item in response.data["products"]]==["Polera DTF"]
    assert "email" not in response.data["business"] and "address" not in response.data["business"]

def test_private_or_suspended_store_is_not_exposed():
    store(public=False)
    assert APIClient().get("/api/v1/public/stores/aurora/").status_code==404

def test_guest_request_creates_server_priced_order():
    business,product=store();client=APIClient()
    response=client.post("/api/v1/public/stores/aurora/orders/",{"product_slug":"polera-dtf","quantity":2,"first_name":"Camila","phone":"+56911111111","customizations":{"talla":"M"},"unit_price":1},format="json")
    order=Order.objects.get(business=business)
    assert response.status_code==201 and order.origin=="public_store"
    assert order.total==24000 and order.items.get().unit_price==12000
    assert Customer.objects.get(business=business).phone=="+56911111111"

def test_guest_request_enforces_minimum_quantity():
    store()
    response=APIClient().post("/api/v1/public/stores/aurora/orders/",{"product_slug":"polera-dtf","quantity":1,"first_name":"Camila","phone":"+56911111111"},format="json")
    assert response.status_code==400 and Order.objects.count()==0
