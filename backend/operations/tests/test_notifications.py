import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from rest_framework.test import APIClient
from businesses.models import Business,BusinessMembership
from operations.models import Notification
from operations.services import notify_business,send_event_email

pytestmark=pytest.mark.django_db
User=get_user_model()

def tenant(name,email):
    business=Business.objects.create(name=name,status="active")
    user=User.objects.create_user(username=email,email=email,password="Marea-Violeta-4821")
    BusinessMembership.objects.create(business=business,user=user,role="owner")
    client=APIClient();client.force_authenticate(user)
    return business,user,client

def test_notifications_are_created_for_active_members_and_isolated():
    first,first_user,client=tenant("Aurora","owner@aurora.cl")
    second,second_user,_=tenant("Tinta Sur","owner@tintasur.cl")
    notify_business(first,"order.public","Nuevo pedido","Detalle","/app/pedidos")
    Notification.objects.create(business=second,recipient=second_user,kind="private",title="Privada")
    response=client.get("/api/v1/notifications/")
    assert response.status_code==200 and response.data["count"]==1
    assert response.data["results"][0]["title"]=="Nuevo pedido"
    assert response.data["results"][0]["is_read"] is False
    item_id=response.data["results"][0]["id"]
    assert client.post(f"/api/v1/notifications/{item_id}/read/").status_code==200
    assert Notification.objects.get(id=item_id).read_at is not None

def test_user_cannot_mark_foreign_notification_as_read():
    _,_,client=tenant("Aurora","owner2@aurora.cl")
    second,second_user,_=tenant("Tinta Sur","owner2@tintasur.cl")
    item=Notification.objects.create(business=second,recipient=second_user,kind="private",title="Privada")
    assert client.post(f"/api/v1/notifications/{item.id}/read/").status_code==404

@pytest.mark.django_db(transaction=True)
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_event_email_is_sent_after_commit_and_escapes_html():
    send_event_email("Pedido <nuevo>","Hola <script>alert(1)</script>",["cliente@example.com"],"https://estampaflow.cl/pedido/seguro")
    assert len(mail.outbox)==1
    message=mail.outbox[0]
    assert message.to==["cliente@example.com"]
    assert "https://estampaflow.cl/pedido/seguro" in message.body
    html=message.alternatives[0][0]
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
