from datetime import timedelta
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from businesses.models import Business,BusinessMembership
from operations.models import Order,Product,ProductCategory,QuoteProposal,QuoteRequest

pytestmark=pytest.mark.django_db

def company(name,email,region="Metropolitana de Santiago",verified=True):
    business=Business.objects.create(name=name,slug=name.lower(),status="active",is_public=True,is_verified=verified,accepts_quotes=True,region=region,national_delivery=True,weekly_capacity=100)
    category=ProductCategory.objects.create(business=business,name="Poleras")
    Product.objects.create(business=business,category=category,name="Polera DTF",slug="polera",is_active=True)
    user=get_user_model().objects.create_user(username=email,email=email,password="Marea-Violeta-4821")
    BusinessMembership.objects.create(business=business,user=user,role="owner")
    return business,user

def quote_payload():return {"title":"20 poleras para equipo","category":"Poleras","product_type":"Polera","description":"Poleras negras con logo","quantity":20,"specifications":{"color":"Negro"},"required_date":str(timezone.localdate()+timedelta(days=15)),"region":"Metropolitana de Santiago","commune":"Santiago","delivery_method":"shipping","contact_name":"Camila Soto","contact_email":"camila@test.cl","contact_phone":"+56911111111"}

def auth(user):c=APIClient();c.force_authenticate(user);return c

def test_deterministic_matching_excludes_unverified_business():
    eligible,_=company("Aurora","a@test.cl");company("Pendiente","p@test.cl",verified=False)
    response=APIClient().post("/api/v1/public/quotes/",quote_payload(),format="json")
    quote=QuoteRequest.objects.get(public_id=response.data["public_id"])
    assert response.status_code==201 and response.data["matches"]==1
    assert quote.matches.get().business==eligible

def test_only_matched_business_can_see_and_answer_request():
    matched,user=company("Aurora","a@test.cl");outside_business,outsider=company("Norte","n@test.cl",region="Antofagasta");outside_business.accepts_quotes=False;outside_business.save(update_fields=["accepts_quotes"])
    quote_id=APIClient().post("/api/v1/public/quotes/",quote_payload(),format="json").data["public_id"];quote=QuoteRequest.objects.get(public_id=quote_id)
    assert auth(user).get("/api/v1/quote-requests/").data["count"]==1
    payload={"request":quote.id,"total_price":"230000","unit_price":"12000","discount":"20000","shipping_cost":"10000","production_days":7,"valid_until":str(timezone.localdate()+timedelta(days=7)),"status":"sent"}
    assert auth(user).post("/api/v1/quote-proposals/",payload,format="json").status_code==201
    assert auth(outsider).post("/api/v1/quote-proposals/",payload,format="json").status_code==400

def test_privacy_and_atomic_acceptance_create_single_winner_order():
    business,user=company("Aurora","a@test.cl");quote_id=APIClient().post("/api/v1/public/quotes/",quote_payload(),format="json").data["public_id"];quote=QuoteRequest.objects.get(public_id=quote_id)
    proposal=QuoteProposal.objects.create(request=quote,business=business,total_price=240000,unit_price=12000,production_days=7,valid_until=timezone.localdate()+timedelta(days=7),created_by=user,status="sent")
    public=APIClient().get(f"/api/v1/public/quotes/{quote.public_id}/")
    assert "contact_email" not in public.data and "contact_phone" not in public.data
    endpoint=f"/api/v1/public/quotes/{quote.public_id}/proposals/{proposal.public_id}/accept/"
    first=APIClient().post(endpoint,{},format="json");second=APIClient().post(endpoint,{},format="json")
    quote.refresh_from_db();proposal.refresh_from_db()
    assert first.status_code==200 and second.status_code==409
    assert quote.accepted_proposal==proposal and proposal.status=="accepted"
    assert Order.objects.filter(business=business,origin="quote").count()==1

def test_companies_never_see_competitor_proposals():
    first,first_user=company("Aurora","a@test.cl");second,second_user=company("Tinta","t@test.cl")
    quote_id=APIClient().post("/api/v1/public/quotes/",quote_payload(),format="json").data["public_id"];quote=QuoteRequest.objects.get(public_id=quote_id)
    QuoteProposal.objects.create(request=quote,business=first,total_price=240000,unit_price=12000,production_days=7,valid_until=timezone.localdate()+timedelta(days=7),created_by=first_user)
    QuoteProposal.objects.create(request=quote,business=second,total_price=220000,unit_price=11000,production_days=8,valid_until=timezone.localdate()+timedelta(days=7),created_by=second_user)
    assert auth(first_user).get("/api/v1/quote-proposals/").data["count"]==1
