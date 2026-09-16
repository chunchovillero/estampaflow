from django.contrib.auth import get_user_model, password_validation
from django.db import transaction
from rest_framework import serializers
from .models import Business, BusinessMembership, BusinessSetting
from .validators import normalize_chilean_phone,normalize_rut
from .territories import valid_location

User = get_user_model()

class BusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        exclude = ("created_at", "updated_at")
        read_only_fields = ("id", "slug", "status", "is_verified")
    def validate_phone(self,value):return normalize_chilean_phone(value)
    def validate_whatsapp(self,value):return normalize_chilean_phone(value)
    def validate_rut(self,value):return normalize_rut(value)
    def validate(self,data):
        region=data.get("region",getattr(self.instance,"region",""));commune=data.get("commune",getattr(self.instance,"commune",""))
        if not valid_location(region,commune):raise serializers.ValidationError({"commune":"La comuna no pertenece a la región seleccionada."})
        return data

class MembershipSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    class Meta:
        model = BusinessMembership
        fields = ("id", "email", "first_name", "last_name", "role", "is_active", "created_at")
        read_only_fields = ("id", "created_at")

class InviteMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=80)
    last_name = serializers.CharField(max_length=80, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=BusinessMembership.Role.choices, default=BusinessMembership.Role.COLLABORATOR)
    def validate_email(self, value):
        if User.objects.filter(email=value.lower().strip()).exists():
            raise serializers.ValidationError("El correo ya está registrado.")
        return value.lower().strip()
    def validate_password(self, value):
        password_validation.validate_password(value)
        return value
    @transaction.atomic
    def create(self, data):
        business = self.context["business"]
        try:
            limit = business.subscription.limit("users")
        except Exception:
            limit = None
        current = business.memberships.filter(is_active=True).count()
        if limit is not None and current >= int(limit):
            raise serializers.ValidationError({"plan": "Alcanzaste el límite de usuarios de tu plan."})
        password = data.pop("password")
        role = data.pop("role")
        email = data.pop("email")
        user = User.objects.create_user(username=email, email=email, password=password, **data)
        return BusinessMembership.objects.create(business=business, user=user, role=role)

class BusinessSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model=BusinessSetting
        fields=("order_prefix","whatsapp_templates","payment_methods","delivery_methods")
