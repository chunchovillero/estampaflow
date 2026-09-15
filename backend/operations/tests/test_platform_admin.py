import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from businesses.models import Business, BusinessMembership
from operations.models import AuditLog, FeaturedBusiness, FeaturedProduct, Product, ProductCategory

pytestmark=pytest.mark.django_db
User=get_user_model()

def authenticated(user):
    client=APIClient();client.force_authenticate(user);return client

def test_platform_endpoints_are_superadmin_only():
    business=Business.objects.create(name="Aurora",status="active")
    owner=User.objects.create_user(username="owner@test.cl",email="owner@test.cl",password="Marea-Violeta-4821")
    BusinessMembership.objects.create(business=business,user=owner,role="owner")
    assert authenticated(owner).get("/api/v1/platform/dashboard/").status_code==403
    assert authenticated(owner).get("/api/v1/platform/businesses/").status_code==403
    assert authenticated(owner).post("/api/v1/platform/featured/",{"kind":"business","target_id":business.id},format="json").status_code==403

def test_superadmin_can_manage_business_and_moderate_product():
    admin=User.objects.create_superuser(username="admin@test.cl",email="admin@test.cl",password="Marea-Violeta-4821")
    business=Business.objects.create(name="Aurora",status="pending",is_public=True)
    category=ProductCategory.objects.create(business=business,name="Poleras")
    product=Product.objects.create(business=business,category=category,name="Polera",slug="polera",is_public=True,moderation_status="pending",sale_price=12990)
    client=authenticated(admin)
    metrics=client.get("/api/v1/platform/dashboard/")
    assert metrics.status_code==200 and metrics.data["pending_products"]==1
    company=client.patch(f"/api/v1/platform/businesses/{business.id}/",{"status":"active","is_verified":True},format="json")
    moderation=client.patch(f"/api/v1/platform/products/{product.id}/",{"moderation_status":"approved"},format="json")
    business.refresh_from_db();product.refresh_from_db()
    assert company.status_code==200 and business.status=="active" and business.is_verified
    assert moderation.status_code==200 and product.moderation_status=="approved"
    assert client.post("/api/v1/platform/featured/",{"kind":"business","target_id":business.id,"position":1},format="json").data["active"] is True
    assert client.post("/api/v1/platform/featured/",{"kind":"product","target_id":product.id,"position":1},format="json").data["active"] is True
    assert FeaturedBusiness.objects.filter(business=business,is_active=True).exists()
    assert FeaturedProduct.objects.filter(product=product,is_active=True).exists()
    assert AuditLog.objects.filter(action="platform.business_updated",business=business,actor=admin).exists()
    assert AuditLog.objects.filter(action="platform.product_moderated",business=business,actor=admin).exists()
    assert len(client.get("/api/v1/platform/dashboard/").data["recent_activity"])==4
    marketplace=APIClient().get("/api/v1/public/marketplace/")
    assert any(item["id"]==product.id for item in marketplace.data["products"])
    assert any(item["id"]==product.id for item in marketplace.data["featured_products"])
    assert client.post("/api/v1/platform/featured/",{"kind":"product","target_id":product.id},format="json").data["active"] is False
    assert not FeaturedProduct.objects.filter(product=product,is_active=True).exists()
