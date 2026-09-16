import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from businesses.models import Business, BusinessMembership, Plan, Subscription

pytestmark = pytest.mark.django_db
User = get_user_model()

def setup_business(name, email, role="owner"):
    business = Business.objects.create(name=name, email=email, status="active")
    user = User.objects.create_user(username=email, email=email, password="Marea-Violeta-4821")
    membership = BusinessMembership.objects.create(business=business, user=user, role=role)
    return business, user, membership

def authenticated(user):
    client = APIClient()
    client.force_authenticate(user)
    return client

def test_each_user_only_gets_own_business():
    first, first_user, _ = setup_business("Tinta Sur", "ana@example.cl")
    second, second_user, _ = setup_business("Color Norte", "leo@example.cl")
    response = authenticated(first_user).get("/api/v1/businesses/current/")
    assert response.status_code == 200
    assert response.data["id"] == first.id
    assert response.data["id"] != second.id
    assert authenticated(second_user).get("/api/v1/businesses/current/").data["id"] == second.id

def test_business_id_from_frontend_is_ignored():
    first, first_user, _ = setup_business("Tinta Sur", "ana@example.cl")
    second, _, _ = setup_business("Color Norte", "leo@example.cl")
    response = authenticated(first_user).patch("/api/v1/businesses/current/", {"id": second.id, "name": "Nuevo nombre", "status": "suspended"}, format="json")
    assert response.status_code == 200
    first.refresh_from_db(); second.refresh_from_db()
    assert first.name == "Nuevo nombre" and first.status == "active"
    assert second.name == "Color Norte"

def test_collaborator_cannot_edit_business_or_manage_team():
    _, user, _ = setup_business("Tinta Sur", "colab@example.cl", "collaborator")
    client = authenticated(user)
    assert client.patch("/api/v1/businesses/current/", {"name": "Ataque"}, format="json").status_code == 403
    assert client.get("/api/v1/businesses/members/").status_code == 403

def test_owner_cannot_update_member_from_other_business():
    _, owner, _ = setup_business("Tinta Sur", "owner@example.cl")
    _, _, foreign_membership = setup_business("Color Norte", "foreign@example.cl", "collaborator")
    response = authenticated(owner).patch(f"/api/v1/businesses/members/{foreign_membership.id}/", {"is_active": False}, format="json")
    assert response.status_code == 404
    foreign_membership.refresh_from_db()
    assert foreign_membership.is_active is True

def test_suspended_business_cannot_use_private_api():
    business, user, _ = setup_business("Tinta Sur", "ana@example.cl")
    business.status = "suspended"; business.save()
    assert authenticated(user).get("/api/v1/businesses/current/").status_code == 403

def test_plan_limits_active_members():
    business, owner, _ = setup_business("Tinta Sur", "owner-limit@example.cl")
    plan = Plan.objects.create(code="one-user", name="Un usuario", limits={"users": 1})
    Subscription.objects.create(business=business, plan=plan)
    response = authenticated(owner).post("/api/v1/businesses/members/", {
        "email":"team-limit@example.cl", "first_name":"Equipo", "password":"Marea-Violeta-4821", "role":"collaborator"
    }, format="json")
    assert response.status_code == 400
    assert not User.objects.filter(email="team-limit@example.cl").exists()

def test_business_sees_own_plan_and_usage():
    from operations.models import Product,ProductCategory
    business,owner,_=setup_business("Tinta Sur","plan-owner@example.cl")
    plan=Plan.objects.create(code="starter",name="Starter",monthly_price=9990,limits={"orders":10,"public_products":2,"users":3,"storage_mb":100,"quote_responses":4})
    Subscription.objects.create(business=business,plan=plan)
    category=ProductCategory.objects.create(business=business,name="Tazones")
    Product.objects.create(business=business,category=category,name="Tazón",slug="tazon",is_public=True)
    response=authenticated(owner).get("/api/v1/businesses/plan/")
    assert response.status_code==200 and response.data["plan"]["code"]=="starter"
    assert response.data["usage"]["users"]==1 and response.data["usage"]["public_products"]==1

def test_only_superadmin_can_edit_plan_limits():
    _,owner,_=setup_business("Tinta Sur","normal-owner@example.cl")
    plan=Plan.objects.create(code="editable",name="Editable",limits={"orders":10})
    endpoint=f"/api/v1/businesses/platform/plans/{plan.id}/"
    assert authenticated(owner).patch(endpoint,{"limits":{"orders":20}},format="json").status_code==403
    admin=User.objects.create_superuser(username="plans-admin@example.cl",email="plans-admin@example.cl",password="Marea-Violeta-4821")
    response=authenticated(admin).patch(endpoint,{"monthly_price":19990,"limits":{"orders":20,"users":5}},format="json")
    plan.refresh_from_db()
    assert response.status_code==200 and plan.monthly_price==19990 and plan.limits=={"orders":20,"users":5}
    assert authenticated(admin).patch(endpoint,{"limits":{"unknown":1}},format="json").status_code==400
