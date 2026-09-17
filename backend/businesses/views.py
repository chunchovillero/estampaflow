from rest_framework import generics, status
from django.db.models import Sum
from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import BusinessMembership,BusinessSetting,Plan,Subscription
from .permissions import HasActiveBusiness, IsBusinessOwner, get_membership
from .serializers import BusinessSerializer,BusinessSettingSerializer,InviteMemberSerializer,MembershipSerializer
from .territories import CHILE_TERRITORIES

class TerritoryView(APIView):
    permission_classes=[permissions.AllowAny];authentication_classes=[]
    def get(self,request):return Response([{"region":region,"communes":communes} for region,communes in CHILE_TERRITORIES.items()])

class CurrentBusinessView(APIView):
    permission_classes = [HasActiveBusiness]
    def get(self, request):
        return Response(BusinessSerializer(get_membership(request.user).business).data)
    def patch(self, request):
        if get_membership(request.user).role != BusinessMembership.Role.OWNER:
            return Response({"error": {"status": 403, "details": "Solo el propietario puede modificar la empresa."}}, status=403)
        business = get_membership(request.user).business
        serializer = BusinessSerializer(business, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class MemberListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsBusinessOwner]
    serializer_class = MembershipSerializer
    def get_queryset(self):
        if getattr(self,"swagger_fake_view",False):return BusinessMembership.objects.none()
        return BusinessMembership.objects.select_related("user").filter(business=get_membership(self.request.user).business)
    def create(self, request, *args, **kwargs):
        serializer = InviteMemberSerializer(data=request.data, context={"business": get_membership(request.user).business})
        serializer.is_valid(raise_exception=True)
        membership = serializer.save()
        return Response(MembershipSerializer(membership).data, status=status.HTTP_201_CREATED)

class MemberDetailView(generics.UpdateAPIView):
    permission_classes = [IsBusinessOwner]
    serializer_class = MembershipSerializer
    http_method_names = ["patch"]
    def get_queryset(self):
        if getattr(self,"swagger_fake_view",False):return BusinessMembership.objects.none()
        return BusinessMembership.objects.filter(business=get_membership(self.request.user).business).exclude(user=self.request.user)

class BusinessSettingView(APIView):
    permission_classes=[HasActiveBusiness]
    def get_object(self,request):return BusinessSetting.objects.get_or_create(business=get_membership(request.user).business)[0]
    def get(self,request):return Response(BusinessSettingSerializer(self.get_object(request)).data)
    def patch(self,request):
        if get_membership(request.user).role!="owner":return Response({"error":{"status":403,"details":"Solo el propietario puede modificar los mensajes."}},status=403)
        serializer=BusinessSettingSerializer(self.get_object(request),data=request.data,partial=True);serializer.is_valid(raise_exception=True);serializer.save();return Response(serializer.data)

class CurrentPlanView(APIView):
    permission_classes=[HasActiveBusiness]
    def get(self,request):
        from operations.models import Order,OrderFile,Product,QuoteProposal
        business=get_membership(request.user).business
        try:subscription=business.subscription
        except Subscription.DoesNotExist:
            free,_=Plan.objects.get_or_create(code="free",defaults={"name":"Gratis","limits":{"orders":30,"public_products":5,"users":2,"storage_mb":100,"quote_responses":3}});subscription=Subscription.objects.create(business=business,plan=free)
        now=timezone.now();usage={"orders":Order.objects.filter(business=business,created_at__year=now.year,created_at__month=now.month).count(),"public_products":Product.objects.filter(business=business,is_public=True,is_active=True).count(),"users":business.memberships.filter(is_active=True).count(),"storage_mb":round((OrderFile.objects.filter(business=business,is_active=True).aggregate(value=Sum("size"))["value"] or 0)/1024/1024,2),"quote_responses":QuoteProposal.objects.filter(business=business,created_at__year=now.year,created_at__month=now.month).count()}
        limits={**subscription.plan.limits,**subscription.overrides}
        return Response({"plan":{"id":subscription.plan_id,"code":subscription.plan.code,"name":subscription.plan.name,"monthly_price":subscription.plan.monthly_price},"status":subscription.status,"limits":limits,"usage":usage,"ends_at":subscription.ends_at})

class PlatformPlanView(APIView):
    permission_classes=[permissions.IsAdminUser]
    allowed_limits={"orders","public_products","users","storage_mb","quote_responses"}
    def get(self,request):
        return Response([{"id":plan.id,"code":plan.code,"name":plan.name,"monthly_price":plan.monthly_price,"limits":plan.limits,"is_active":plan.is_active,"position":plan.position,"subscriptions":plan.subscriptions.count()} for plan in Plan.objects.order_by("position","monthly_price")])
    def patch(self,request,pk):
        plan=Plan.objects.filter(pk=pk).first()
        if not plan:return Response(status=404)
        if "name" in request.data:plan.name=str(request.data["name"])[:80]
        if "monthly_price" in request.data:
            try:plan.monthly_price=max(0,int(request.data["monthly_price"]))
            except (TypeError,ValueError):return Response({"error":{"status":400,"details":"Precio no válido."}},status=400)
        if "limits" in request.data:
            limits=request.data["limits"]
            if not isinstance(limits,dict) or set(limits)-self.allowed_limits:return Response({"error":{"status":400,"details":"Límites no válidos."}},status=400)
            try:plan.limits={key:max(0,int(value)) for key,value in limits.items()}
            except (TypeError,ValueError):return Response({"error":{"status":400,"details":"Los límites deben ser números enteros."}},status=400)
        if "is_active" in request.data:plan.is_active=bool(request.data["is_active"])
        plan.save();return Response({"id":plan.id,"name":plan.name,"monthly_price":plan.monthly_price,"limits":plan.limits,"is_active":plan.is_active})
