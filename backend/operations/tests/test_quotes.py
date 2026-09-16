from datetime import timedelta
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient
from businesses.models import Business,BusinessMembership
from operations.models import Conversation,Message,Order,Product,ProductCategory,QuoteFile,QuoteProposal,QuoteRequest

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
    assert APIClient().get(f"/api/v1/public/quotes/{quote.public_id}/").status_code==404
    public=APIClient().get(f"/api/v1/public/quotes/{quote.public_id}/?token={quote.access_token}")
    assert "contact_email" not in public.data and "contact_phone" not in public.data
    endpoint=f"/api/v1/public/quotes/{quote.public_id}/proposals/{proposal.public_id}/accept/"
    assert APIClient().post(endpoint,{"token":"00000000-0000-0000-0000-000000000000"},format="json").status_code==404
    first=APIClient().post(endpoint,{"token":str(quote.access_token)},format="json");second=APIClient().post(endpoint,{"token":str(quote.access_token)},format="json")
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
    own=QuoteProposal.objects.get(business=first)
    pdf=auth(first_user).get(f"/api/v1/quote-proposals/{own.id}/pdf/")
    assert pdf.status_code==200 and pdf["Content-Type"]=="application/pdf"
    assert auth(second_user).get(f"/api/v1/quote-proposals/{own.id}/pdf/").status_code==404

def test_quote_files_require_token_and_only_reach_matched_businesses():
    business,user=company("Aurora","files@test.cl");outside_business,outsider=company("Norte","files-norte@test.cl",region="Antofagasta");outside_business.accepts_quotes=False;outside_business.save(update_fields=["accepts_quotes"])
    created=APIClient().post("/api/v1/public/quotes/",quote_payload(),format="json");quote=QuoteRequest.objects.get(public_id=created.data["public_id"])
    upload=SimpleUploadedFile("referencia.pdf",b"%PDF-1.4 demo",content_type="application/pdf")
    endpoint=f"/api/v1/public/quotes/{quote.public_id}/files/"
    assert APIClient().post(endpoint,{"file":upload},format="multipart").status_code==404
    upload=SimpleUploadedFile("referencia.pdf",b"%PDF-1.4 demo",content_type="application/pdf")
    response=APIClient().post(endpoint,{"token":str(quote.access_token),"file":upload},format="multipart")
    item=QuoteFile.objects.get(id=response.data["id"])
    assert response.status_code==201 and auth(user).get("/api/v1/quote-files/").data[0]["id"]==item.id
    assert auth(outsider).get(f"/api/v1/quote-files/{item.id}/").status_code==404
    assert APIClient().get(f"{endpoint}{item.id}/?token={quote.access_token}").status_code==200

def test_conversation_marks_messages_read_and_rejects_foreign_attachments():
    first,first_user=company("Aurora","chat-a@test.cl");second,second_user=company("Tinta","chat-b@test.cl")
    created=APIClient().post("/api/v1/public/quotes/",quote_payload(),format="json");quote=QuoteRequest.objects.get(public_id=created.data["public_id"])
    first_proposal=QuoteProposal.objects.create(request=quote,business=first,total_price=240000,unit_price=12000,production_days=7,valid_until=timezone.localdate()+timedelta(days=7),created_by=first_user,status="sent")
    second_proposal=QuoteProposal.objects.create(request=quote,business=second,total_price=220000,unit_price=11000,production_days=8,valid_until=timezone.localdate()+timedelta(days=7),created_by=second_user,status="sent")
    first_chat=Conversation.objects.create(proposal=first_proposal);Conversation.objects.create(proposal=second_proposal)
    client_message=Message.objects.create(conversation=first_chat,sender_type="client",body="¿Incluye despacho?")
    foreign_file=QuoteFile.objects.create(request=quote,proposal=second_proposal,business=second,file=SimpleUploadedFile("otra.pdf",b"%PDF-1.4 demo",content_type="application/pdf"),original_name="otra.pdf",mime_type="application/pdf",size=13,sender_type="business",uploaded_by=second_user)
    endpoint=f"/api/v1/quote-proposals/{first_proposal.id}/messages/"
    assert auth(first_user).post(endpoint,{"body":"Respuesta","file_id":foreign_file.id},format="json").status_code==400
    messages=auth(first_user).get(endpoint)
    client_message.refresh_from_db()
    assert messages.status_code==200 and client_message.is_read is True
    business_message=Message.objects.create(conversation=first_chat,sender_type="business",sender_user=first_user,body="Sí, está incluido")
    cache.clear()
    APIClient().get(f"/api/v1/public/quotes/{quote.public_id}/?token={quote.access_token}")
    business_message.refresh_from_db()
    assert business_message.is_read is True
