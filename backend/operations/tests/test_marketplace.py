import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from businesses.models import Business,BusinessMembership
from operations.models import FeaturedBusiness,FeaturedProduct,Product,ProductCategory

pytestmark=pytest.mark.django_db

def product_data(name="Polera DTF",region="Metropolitana de Santiago",approved=True):
    business=Business.objects.create(name=f"Tienda {name}",slug=name.lower().replace(" ","-"),status="active",is_public=True,is_verified=True,region=region,national_delivery=True)
    category=ProductCategory.objects.create(business=business,name="Poleras")
    product=Product.objects.create(business=business,category=category,name=name,slug="producto",sale_price=12000,is_public=True,moderation_status="approved" if approved else "pending")
    return business,product

def test_marketplace_only_shows_moderated_products_and_filters():
    business,approved=product_data();product_data("Producto pendiente",approved=False)
    response=APIClient().get("/api/v1/public/marketplace/",{"search":"Polera","region":"Metropolitana de Santiago","delivery":"national"})
    assert response.status_code==200
    assert [p["id"] for p in response.data["products"]]==[approved.id]
    assert response.data["products"][0]["business"]["slug"]==business.slug

def test_featured_placements_are_selected_by_backend():
    business,product=product_data();FeaturedBusiness.objects.create(business=business,position=1);FeaturedProduct.objects.create(product=product,position=1)
    data=APIClient().get("/api/v1/public/marketplace/").data
    assert data["featured_businesses"][0]["slug"]==business.slug
    assert data["featured_products"][0]["id"]==product.id

def test_business_cannot_self_approve_product():
    business,product=product_data(approved=False);User=get_user_model();user=User.objects.create_user(username="owner@test.cl",email="owner@test.cl",password="Marea-Violeta-4821");BusinessMembership.objects.create(business=business,user=user,role="owner")
    client=APIClient();client.force_authenticate(user)
    response=client.patch(f"/api/v1/products/{product.id}/",{"moderation_status":"approved"},format="json")
    product.refresh_from_db()
    assert response.status_code==200 and product.moderation_status=="pending"
