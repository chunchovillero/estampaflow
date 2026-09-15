from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import BusinessMembership,BusinessSetting
from .permissions import HasActiveBusiness, IsBusinessOwner, get_membership
from .serializers import BusinessSerializer,BusinessSettingSerializer,InviteMemberSerializer,MembershipSerializer

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
        return BusinessMembership.objects.filter(business=get_membership(self.request.user).business).exclude(user=self.request.user)

class BusinessSettingView(APIView):
    permission_classes=[HasActiveBusiness]
    def get_object(self,request):return BusinessSetting.objects.get_or_create(business=get_membership(request.user).business)[0]
    def get(self,request):return Response(BusinessSettingSerializer(self.get_object(request)).data)
    def patch(self,request):
        if get_membership(request.user).role!="owner":return Response({"error":{"status":403,"details":"Solo el propietario puede modificar los mensajes."}},status=403)
        serializer=BusinessSettingSerializer(self.get_object(request),data=request.data,partial=True);serializer.is_valid(raise_exception=True);serializer.save();return Response(serializer.data)
