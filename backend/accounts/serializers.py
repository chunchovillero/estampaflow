from django.contrib.auth import get_user_model, password_validation
from django.db import transaction
from rest_framework import serializers
from businesses.models import Business,BusinessMembership,Plan,Subscription

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    business = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "phone", "email_verified", "is_superuser", "role", "business")
    def _membership(self, obj):
        return obj.memberships.select_related("business").filter(is_active=True).first()
    def get_role(self, obj):
        membership = self._membership(obj)
        return membership.role if membership else ("superadmin" if obj.is_superuser else None)
    def get_business(self, obj):
        membership = self._membership(obj)
        return {"id": membership.business_id, "name": membership.business.name, "slug": membership.business.slug} if membership else None

class RegisterSerializer(serializers.Serializer):
    business_name = serializers.CharField(max_length=160)
    first_name = serializers.CharField(max_length=80)
    last_name = serializers.CharField(max_length=80, required=False, allow_blank=True)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)
    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Ya existe una cuenta con este correo.")
        return value
    def validate_password(self, value):
        password_validation.validate_password(value)
        return value
    @transaction.atomic
    def create(self, data):
        business_name = data.pop("business_name")
        email = data.pop("email")
        password = data.pop("password")
        user = User.objects.create_user(username=email, email=email, password=password, **data)
        business = Business.objects.create(name=business_name, email=email, status=Business.Status.ACTIVE)
        free,_=Plan.objects.get_or_create(code="free",defaults={"name":"Gratis","limits":{"orders":30,"public_products":5,"users":2,"storage_mb":100,"quote_responses":3}})
        Subscription.objects.create(business=business,plan=free)
        BusinessMembership.objects.create(user=user, business=business, role=BusinessMembership.Role.OWNER)
        return user

class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone")

class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("La contraseña actual no es correcta.")
        return value
    def validate_new_password(self, value):
        password_validation.validate_password(value, self.context["request"].user)
        return value
