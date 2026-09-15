from datetime import timedelta
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient
from businesses.models import Business,BusinessMembership
from operations.models import Customer,DesignApproval,Order,OrderFile,OrderItem

pytestmark=pytest.mark.django_db
def setup(name,email):
    business=Business.objects.create(name=name,status="active");user=get_user_model().objects.create_user(username=email,email=email,password="Test-1234-segura");BusinessMembership.objects.create(business=business,user=user,role="owner");customer=Customer.objects.create(business=business,first_name="Ana",phone="1");order=Order.objects.create(business=business,number=1,customer=customer);OrderItem.objects.create(business=business,order=order,description="Polera",quantity=1,unit_price=10000);client=APIClient();client.force_authenticate(user);return business,user,order,client

def test_file_upload_validates_content_and_is_tenant_protected():
    business,user,order,client=setup("Aurora","a@test.cl");fake=SimpleUploadedFile("diseno.pdf",b"%PDF-1.4 demo",content_type="application/pdf")
    uploaded=client.post("/api/v1/order-files/",{"order":order.id,"kind":"final","file":fake},format="multipart")
    assert uploaded.status_code==201
    _,_,_,other=setup("Otra","o@test.cl")
    assert other.get(f"/api/v1/order-files/{uploaded.data['id']}/download/").status_code==404

def test_rejects_extension_content_mismatch():
    _,_,order,client=setup("Aurora","a@test.cl");fake=SimpleUploadedFile("ataque.pdf",b"not a pdf",content_type="application/pdf")
    assert client.post("/api/v1/order-files/",{"order":order.id,"kind":"final","file":fake},format="multipart").status_code==400

def test_public_approval_is_immutable_and_updates_order():
    _,user,order,client=setup("Aurora","a@test.cl");approval=DesignApproval.objects.create(order=order,created_by=user,expires_at=timezone.now()+timedelta(days=2))
    endpoint=f"/api/v1/public/approvals/{approval.token}/";public=APIClient()
    assert public.post(endpoint,{"action":"approve","name":"Ana","comment":"Está perfecto"},format="json").status_code==200
    order.refresh_from_db();approval.refresh_from_db();assert order.status=="approved" and approval.approved_by_name=="Ana"
    assert public.post(endpoint,{"action":"approve","name":"Ana"},format="json").status_code==410

def test_expired_or_revoked_approval_cannot_be_used():
    _,user,order,_=setup("Aurora","a@test.cl");approval=DesignApproval.objects.create(order=order,created_by=user,expires_at=timezone.now()-timedelta(minutes=1))
    assert APIClient().get(f"/api/v1/public/approvals/{approval.token}/").status_code==410
    assert APIClient().post(f"/api/v1/public/approvals/{approval.token}/",{"action":"approve","name":"Ana"},format="json").status_code==410
