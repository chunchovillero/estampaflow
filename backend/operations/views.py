from django.db import transaction
from django.http import FileResponse,HttpResponse
from django.db.models import Count, Sum, Q
from django.utils import timezone
from rest_framework import decorators, permissions, response, status, viewsets
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from businesses.models import Business
from businesses.permissions import HasActiveBusiness, get_membership
from .models import Conversation,Customer,DesignApproval,DesignChangeRequest,FeaturedBusiness,FeaturedProduct,Message,Order,OrderFile,OrderItem,OrderStatusHistory,Payment,Product,ProductCategory,QuoteProposal,QuoteRequest
from .serializers import CategorySerializer,CustomerSerializer,DesignApprovalSerializer,MarketplaceProductSerializer,MessageSerializer,OrderFileSerializer,OrderListSerializer,OrderSerializer,PaymentSerializer,ProductSerializer,PublicOrderRequestSerializer,PublicProductSerializer,PublicProposalSerializer,QuoteProposalSerializer,QuoteRequestBusinessSerializer,QuoteRequestCreateSerializer
from .services import enforce_plan_limit,next_order_number,recalculate_order

class TenantViewSet(viewsets.ModelViewSet):
    permission_classes=[HasActiveBusiness]
    def business(self): return get_membership(self.request.user).business
    def perform_create(self, serializer): serializer.save(business=self.business())

class CustomerViewSet(TenantViewSet):
    serializer_class=CustomerSerializer
    search_fields=("first_name","last_name","phone","email","instagram")
    ordering_fields=("first_name","created_at")
    filterset_fields=("is_active","region","commune")
    def get_queryset(self): return Customer.objects.filter(business=self.business())
    def perform_destroy(self, instance):
        if instance.orders.exists(): instance.is_active=False; instance.save(update_fields=["is_active"])
        else: instance.delete()

class CategoryViewSet(TenantViewSet):
    serializer_class=CategorySerializer
    def get_queryset(self): return ProductCategory.objects.filter(business=self.business())

class ProductViewSet(TenantViewSet):
    serializer_class=ProductSerializer
    search_fields=("name","short_description","description")
    ordering_fields=("name","sale_price","created_at","stock")
    filterset_fields=("category","is_active","is_public","price_type")
    def get_queryset(self): return Product.objects.filter(business=self.business()).select_related("category").prefetch_related("variants")
    def perform_destroy(self, instance):
        if instance.order_items.exists(): instance.is_active=False; instance.save(update_fields=["is_active"])
        else: instance.delete()

class OrderViewSet(TenantViewSet):
    search_fields=("customer__first_name","customer__last_name","number")
    ordering_fields=("created_at","due_date","total","priority")
    filterset_fields=("status","priority","origin","customer","responsible","payment_status")
    def get_queryset(self): return Order.objects.filter(business=self.business()).select_related("customer","responsible").prefetch_related("items","payments","status_history").annotate(items_count=Count("items"))
    def get_serializer_class(self): return OrderListSerializer if self.action=="list" else OrderSerializer
    @decorators.action(detail=True,methods=["post"])
    def change_status(self,request,pk=None):
        order=self.get_object(); serializer=OrderSerializer(order,data={"status":request.data.get("status")},partial=True,context={"request":request});serializer.is_valid(raise_exception=True);serializer.save();return response.Response(OrderSerializer(order,context={"request":request}).data)

class PaymentViewSet(TenantViewSet):
    serializer_class=PaymentSerializer
    filterset_fields=("order","method","is_void")
    ordering_fields=("paid_at","amount")
    def get_queryset(self): return Payment.objects.filter(business=self.business()).select_related("order","registered_by")
    def perform_destroy(self,instance):
        from .services import recalculate_order
        instance.is_void=True;instance.save(update_fields=["is_void"]);recalculate_order(instance.order)

@decorators.api_view(["GET"])
def dashboard(request):
    membership=get_membership(request.user)
    if not membership or membership.business.status!="active": return response.Response(status=status.HTTP_403_FORBIDDEN)
    orders=Order.objects.filter(business=membership.business);today=timezone.localdate();month=today.replace(day=1)
    values={"new":orders.filter(status="new").count(),"overdue":orders.filter(due_date__lt=today).exclude(status__in=("delivered","cancelled")).count(),"due_today":orders.filter(due_date=today).exclude(status__in=("delivered","cancelled")).count(),"waiting_approval":orders.filter(status="waiting_approval").count(),"production":orders.filter(status="production").count(),"ready":orders.filter(status="ready").count(),"pending_balance":orders.aggregate(v=Sum("balance"))["v"] or 0,"monthly_sales":orders.filter(created_at__date__gte=month).exclude(status="cancelled").aggregate(v=Sum("total"))["v"] or 0,"monthly_payments":Payment.objects.filter(business=membership.business,paid_at__date__gte=month,is_void=False).aggregate(v=Sum("amount"))["v"] or 0}
    return response.Response(values)

class PublicStoreView(APIView):
    permission_classes=[permissions.AllowAny];authentication_classes=[]
    def get_business(self,slug): return Business.objects.filter(slug=slug,status="active",is_public=True).first()
    def get(self,request,slug,product_slug=None):
        business=self.get_business(slug)
        if not business:return response.Response({"error":{"status":404,"details":"Tienda no encontrada."}},status=404)
        products=Product.objects.filter(business=business,is_active=True,is_public=True).exclude(moderation_status__in=("rejected","hidden")).select_related("category").prefetch_related("variants")
        if product_slug:
            product=products.filter(slug=product_slug).first()
            if not product:return response.Response({"error":{"status":404,"details":"Producto no encontrado."}},status=404)
            return response.Response({"business":self.business_data(business),"product":PublicProductSerializer(product,context={"request":request}).data})
        if request.query_params.get("category"):products=products.filter(category_id=request.query_params["category"])
        if request.query_params.get("search"):products=products.filter(Q(name__icontains=request.query_params["search"])|Q(description__icontains=request.query_params["search"]))
        categories=ProductCategory.objects.filter(business=business,is_active=True,products__is_public=True,products__is_active=True).distinct().values("id","name")
        return response.Response({"business":self.business_data(business),"categories":list(categories),"products":PublicProductSerializer(products,many=True,context={"request":request}).data})
    @staticmethod
    def business_data(b):return {"name":b.name,"slug":b.slug,"description":b.description,"logo":b.logo.url if b.logo else None,"banner":b.banner.url if b.banner else None,"primary_color":b.primary_color,"secondary_color":b.secondary_color,"whatsapp":b.whatsapp,"instagram":b.instagram,"region":b.region,"commune":b.commune,"allows_pickup":b.allows_pickup,"local_delivery":b.local_delivery,"national_delivery":b.national_delivery,"average_response_hours":b.average_response_hours}

class PublicOrderRequestView(APIView):
    permission_classes=[permissions.AllowAny];authentication_classes=[];throttle_classes=[ScopedRateThrottle];throttle_scope="public_order"
    def post(self,request,slug):
        business=Business.objects.filter(slug=slug,status="active",is_public=True).first()
        if not business:return response.Response({"error":{"status":404,"details":"Tienda no encontrada."}},status=404)
        serializer=PublicOrderRequestSerializer(data=request.data,context={"business":business});serializer.is_valid(raise_exception=True);order=serializer.save()
        return response.Response({"public_id":order.public_id,"display_number":order.display_number,"status":order.status,"detail":"Solicitud recibida. El emprendimiento revisará tu pedido."},status=201)

class MarketplaceView(APIView):
    permission_classes=[permissions.AllowAny];authentication_classes=[]
    def get(self,request):
        now=timezone.now()
        products=Product.objects.filter(business__status="active",business__is_public=True,is_active=True,is_public=True,moderation_status="approved").select_related("business","category").prefetch_related("variants")
        q=request.query_params.get("search")
        if q:products=products.filter(Q(name__icontains=q)|Q(short_description__icontains=q)|Q(description__icontains=q)|Q(business__name__icontains=q))
        if request.query_params.get("category"):products=products.filter(category__name__iexact=request.query_params["category"])
        if request.query_params.get("region"):products=products.filter(business__region__iexact=request.query_params["region"])
        if request.query_params.get("price_type"):products=products.filter(price_type=request.query_params["price_type"])
        if request.query_params.get("min_price"):products=products.filter(sale_price__gte=request.query_params["min_price"])
        if request.query_params.get("max_price"):products=products.filter(sale_price__lte=request.query_params["max_price"])
        if request.query_params.get("delivery")=="national":products=products.filter(business__national_delivery=True)
        if request.query_params.get("delivery")=="pickup":products=products.filter(business__allows_pickup=True)
        if request.query_params.get("max_days"):products=products.filter(production_days__lte=request.query_params["max_days"])
        featured_ids=FeaturedProduct.objects.filter(is_active=True).filter(Q(starts_at__isnull=True)|Q(starts_at__lte=now)).filter(Q(ends_at__isnull=True)|Q(ends_at__gte=now)).values_list("product_id",flat=True)
        featured_products=products.filter(id__in=featured_ids).order_by("featured_placements__position")[:8]
        featured_business_ids=FeaturedBusiness.objects.filter(is_active=True).filter(Q(starts_at__isnull=True)|Q(starts_at__lte=now)).filter(Q(ends_at__isnull=True)|Q(ends_at__gte=now)).values_list("business_id",flat=True)
        businesses=Business.objects.filter(id__in=featured_business_ids,status="active",is_public=True).order_by("featured_placements__position")[:8]
        categories=list(ProductCategory.objects.filter(products__in=products).values_list("name",flat=True).distinct().order_by("name"))
        regions=list(Business.objects.filter(product__in=products).exclude(region="").values_list("region",flat=True).distinct().order_by("region"))
        return response.Response({"products":MarketplaceProductSerializer(products[:60],many=True,context={"request":request}).data,"featured_products":MarketplaceProductSerializer(featured_products,many=True,context={"request":request}).data,"featured_businesses":[PublicStoreView.business_data(b) for b in businesses],"categories":categories,"regions":regions})

class PublicQuoteRequestView(APIView):
    permission_classes=[permissions.AllowAny];authentication_classes=[];throttle_classes=[ScopedRateThrottle];throttle_scope="public_order"
    def post(self,request):
        serializer=QuoteRequestCreateSerializer(data=request.data);serializer.is_valid(raise_exception=True);quote=serializer.save()
        return response.Response({"public_id":quote.public_id,"matches":quote.matches.count(),"detail":"Solicitud creada. Guarda este enlace para revisar tus propuestas."},status=201)
    def get(self,request,public_id):
        quote=QuoteRequest.objects.filter(public_id=public_id).prefetch_related("proposals__business","proposals__conversation__messages").first()
        if not quote:return response.Response(status=404)
        proposals=quote.proposals.filter(status__in=("sent","viewed","accepted","rejected"))
        proposals.filter(status="sent").update(status="viewed")
        return response.Response({"public_id":quote.public_id,"title":quote.title,"category":quote.category,"description":quote.description,"quantity":quote.quantity,"required_date":quote.required_date,"region":quote.region,"commune":quote.commune,"status":quote.status,"proposals":PublicProposalSerializer(proposals,many=True).data})

class AvailableQuoteViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes=[HasActiveBusiness];serializer_class=QuoteRequestBusinessSerializer
    def get_queryset(self):
        business=get_membership(self.request.user).business
        return QuoteRequest.objects.filter(matches__business=business,matches__is_active=True,status__in=("open","proposals")).annotate(match_score=Sum("matches__score")).distinct().order_by("-created_at")

class QuoteProposalViewSet(viewsets.ModelViewSet):
    permission_classes=[HasActiveBusiness];serializer_class=QuoteProposalSerializer
    http_method_names=["get","post","patch","head","options"]
    def get_queryset(self):return QuoteProposal.objects.filter(business=get_membership(self.request.user).business).select_related("request","business").prefetch_related("conversation__messages")
    @decorators.action(detail=True,methods=["get","post"])
    def messages(self,request,pk=None):
        proposal=self.get_object();conversation,_=Conversation.objects.get_or_create(proposal=proposal)
        if request.method=="POST":
            serializer=MessageSerializer(data=request.data);serializer.is_valid(raise_exception=True);serializer.save(conversation=conversation,sender_type="business",sender_user=request.user)
        return response.Response(MessageSerializer(conversation.messages.all(),many=True).data)

class PublicQuoteMessageView(APIView):
    permission_classes=[permissions.AllowAny];authentication_classes=[];throttle_classes=[ScopedRateThrottle];throttle_scope="public_order"
    def post(self,request,public_id,proposal_id):
        proposal=QuoteProposal.objects.filter(public_id=proposal_id,request__public_id=public_id).first()
        if not proposal:return response.Response(status=404)
        serializer=MessageSerializer(data=request.data);serializer.is_valid(raise_exception=True);conversation,_=Conversation.objects.get_or_create(proposal=proposal);serializer.save(conversation=conversation,sender_type="client")
        return response.Response(serializer.data,status=201)

class AcceptProposalView(APIView):
    permission_classes=[permissions.AllowAny];authentication_classes=[];throttle_classes=[ScopedRateThrottle];throttle_scope="public_order"
    @transaction.atomic
    def post(self,request,public_id,proposal_id):
        quote=QuoteRequest.objects.select_for_update().filter(public_id=public_id).first()
        if not quote:return response.Response(status=404)
        if quote.accepted_proposal_id:return response.Response({"error":{"status":409,"details":"Esta solicitud ya tiene una propuesta aceptada."}},status=409)
        proposal=QuoteProposal.objects.select_for_update().filter(public_id=proposal_id,request=quote,status__in=("sent","viewed")).first()
        if not proposal:return response.Response({"error":{"status":400,"details":"La propuesta no está disponible."}},status=400)
        business=proposal.business
        now=timezone.now();enforce_plan_limit(business,"orders",Order.objects.filter(business=business,created_at__year=now.year,created_at__month=now.month).count())
        customer=Customer.objects.filter(business=business,email=quote.contact_email).first() or Customer.objects.create(business=business,first_name=quote.contact_name,phone=quote.contact_phone,whatsapp=quote.contact_whatsapp,email=quote.contact_email,region=quote.region,commune=quote.commune)
        order=Order.objects.create(business=business,number=next_order_number(business),customer=customer,origin="quote",due_date=proposal.estimated_delivery,discount=proposal.discount,shipping_cost=proposal.shipping_cost,customer_instructions=quote.description)
        OrderItem.objects.create(business=business,order=order,description=quote.title,quantity=quote.quantity,unit_price=proposal.unit_price,unit_cost=0,customizations=quote.specifications)
        recalculate_order(order);OrderStatusHistory.objects.create(order=order,to_status="new",changed_by=proposal.created_by,comment="Creado desde cotización aceptada")
        proposal.status="accepted";proposal.save(update_fields=["status"]);quote.proposals.exclude(id=proposal.id).filter(status__in=("sent","viewed","draft")).update(status="rejected")
        quote.accepted_proposal=proposal;quote.status="accepted";quote.save(update_fields=["accepted_proposal","status"])
        return response.Response({"detail":"Propuesta aceptada y pedido creado.","order_public_id":order.public_id,"display_number":order.display_number})

ALLOWED_FILES={".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg",".webp":"image/webp",".pdf":"application/pdf"}
MAX_FILE_SIZE=10*1024*1024
class OrderFileViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes=[HasActiveBusiness];serializer_class=OrderFileSerializer
    def get_queryset(self):return OrderFile.objects.filter(business=get_membership(self.request.user).business,is_active=True)
    def create(self,request):
        import os
        business=get_membership(request.user).business;upload=request.FILES.get("file");order=Order.objects.filter(id=request.data.get("order"),business=business).first()
        if not upload or not order:return response.Response({"error":{"status":400,"details":"Archivo y pedido son obligatorios."}},status=400)
        ext=os.path.splitext(upload.name)[1].lower();expected=ALLOWED_FILES.get(ext)
        if not expected or upload.content_type!=expected or upload.size>MAX_FILE_SIZE:return response.Response({"error":{"status":400,"details":"Archivo no permitido. Usa PNG, JPG, WEBP o PDF de hasta 10 MB."}},status=400)
        head=upload.read(12);upload.seek(0)
        valid=(expected=="application/pdf" and head.startswith(b"%PDF")) or (expected=="image/png" and head.startswith(b"\x89PNG")) or (expected=="image/jpeg" and head.startswith(b"\xff\xd8")) or (expected=="image/webp" and head[8:12]==b"WEBP")
        if not valid:return response.Response({"error":{"status":400,"details":"El contenido no coincide con el tipo declarado."}},status=400)
        item=None
        if request.data.get("item"):item=OrderItem.objects.filter(id=request.data["item"],order=order,business=business).first()
        obj=OrderFile.objects.create(business=business,order=order,item=item,file=upload,kind=request.data.get("kind","reference"),original_name=os.path.basename(upload.name),mime_type=expected,size=upload.size,uploaded_by=request.user)
        return response.Response(OrderFileSerializer(obj).data,status=201)
    @decorators.action(detail=True,methods=["get"])
    def download(self,request,pk=None):
        obj=self.get_object();return FileResponse(obj.file.open("rb"),content_type=obj.mime_type,as_attachment=True,filename=obj.original_name)

class DesignApprovalViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes=[HasActiveBusiness];serializer_class=DesignApprovalSerializer
    def get_queryset(self):return DesignApproval.objects.filter(order__business=get_membership(self.request.user).business)
    def create(self,request):
        order=Order.objects.filter(id=request.data.get("order"),business=get_membership(request.user).business).first()
        if not order:return response.Response(status=404)
        approval=DesignApproval.objects.create(order=order,expires_at=request.data.get("expires_at") or None,created_by=request.user)
        if order.status!="waiting_approval":old=order.status;order.status="waiting_approval";order.save(update_fields=["status"]);OrderStatusHistory.objects.create(order=order,from_status=old,to_status=order.status,changed_by=request.user)
        return response.Response(DesignApprovalSerializer(approval).data,status=201)
    @decorators.action(detail=True,methods=["post"])
    def revoke(self,request,pk=None):
        approval=self.get_object();approval.revoked_at=timezone.now();approval.save(update_fields=["revoked_at"]);return response.Response(DesignApprovalSerializer(approval).data)

class PublicApprovalView(APIView):
    permission_classes=[permissions.AllowAny];authentication_classes=[];throttle_classes=[ScopedRateThrottle];throttle_scope="public_order"
    def get_object(self,token):return DesignApproval.objects.filter(token=token).select_related("order__customer","order__business").prefetch_related("order__items","order__files","change_requests").first()
    def get(self,request,token):
        approval=self.get_object(token)
        if not approval:return response.Response(status=404)
        if approval.revoked_at or (approval.expires_at and approval.expires_at <= timezone.now()):
            return response.Response({"error":{"status":410,"details":"El enlace venció o fue revocado."}},status=410)
        order=approval.order;files=[{"id":f.id,"name":f.original_name,"kind":f.kind,"url":f"/api/v1/public/approvals/{token}/files/{f.id}/"} for f in order.files.filter(is_active=True,kind__in=("draft","final","reference"))]
        return response.Response({"business":order.business.name,"order":order.display_number,"customer":order.customer.full_name,"items":[{"description":i.description,"quantity":i.quantity,"customizations":i.customizations} for i in order.items.all()],"files":files,"expires_at":approval.expires_at,"approved_at":approval.approved_at,"revoked_at":approval.revoked_at,"changes":[{"comment":c.comment,"created_at":c.created_at} for c in approval.change_requests.all()]})
    @transaction.atomic
    def post(self,request,token):
        approval=DesignApproval.objects.select_for_update().filter(token=token).select_related("order").first()
        if not approval or not approval.is_available:return response.Response({"error":{"status":410,"details":"El enlace venció, fue revocado o ya se utilizó."}},status=410)
        name=request.data.get("name","").strip();comment=request.data.get("comment","").strip();ip=request.META.get("REMOTE_ADDR")
        if not name:return response.Response({"error":{"status":400,"details":"Indica tu nombre."}},status=400)
        if request.data.get("action")=="approve":approval.approved_at=timezone.now();approval.approved_by_name=name;approval.comment=comment;approval.ip_address=ip;approval.save(update_fields=["approved_at","approved_by_name","comment","ip_address"]);old=approval.order.status;approval.order.status="approved";approval.order.save(update_fields=["status"]);OrderStatusHistory.objects.create(order=approval.order,from_status=old,to_status="approved",changed_by=approval.created_by,comment="Diseño aprobado por cliente")
        elif request.data.get("action")=="changes" and comment:DesignChangeRequest.objects.create(approval=approval,requested_by_name=name,comment=comment,ip_address=ip);old=approval.order.status;approval.order.status="changes_requested";approval.order.save(update_fields=["status"]);OrderStatusHistory.objects.create(order=approval.order,from_status=old,to_status="changes_requested",changed_by=approval.created_by,comment="Cliente solicitó cambios")
        else:return response.Response({"error":{"status":400,"details":"Acción o comentario no válido."}},status=400)
        return response.Response({"detail":"Respuesta registrada correctamente."})
    def file(self,request,token,file_id):pass

@decorators.api_view(["GET"])
@decorators.permission_classes([permissions.AllowAny])
def public_approval_file(request,token,file_id):
    approval=DesignApproval.objects.filter(token=token,revoked_at__isnull=True).first();obj=OrderFile.objects.filter(id=file_id,order=approval.order,is_active=True).first() if approval else None
    if approval and approval.expires_at and approval.expires_at <= timezone.now():obj=None
    if not obj:return response.Response(status=404)
    return FileResponse(obj.file.open("rb"),content_type=obj.mime_type,filename=obj.original_name)

@decorators.api_view(["GET"])
def order_pdf(request,pk):
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    business=get_membership(request.user).business;order=Order.objects.filter(id=pk,business=business).select_related("customer").prefetch_related("items","payments").first()
    if not order:return response.Response(status=404)
    buffer=BytesIO();pdf=canvas.Canvas(buffer,pagesize=A4);y=800;pdf.setFont("Helvetica-Bold",18);pdf.drawString(45,y,f"Ficha de producción {order.display_number}");y-=35;pdf.setFont("Helvetica",11)
    for line in [f"Cliente: {order.customer.full_name}",f"Entrega: {order.due_date or 'Sin fecha'}",f"Estado: {order.get_status_display()}",f"Total: ${order.total:,.0f}",f"Pagado: ${order.total_paid:,.0f}",f"Saldo: ${order.balance:,.0f}"]:pdf.drawString(45,y,line);y-=18
    y-=10;pdf.setFont("Helvetica-Bold",12);pdf.drawString(45,y,"Productos");y-=22;pdf.setFont("Helvetica",10)
    for item in order.items.all():pdf.drawString(45,y,f"{item.quantity} x {item.description} - {item.customizations}");y-=18
    pdf.showPage();pdf.save();buffer.seek(0);return FileResponse(buffer,as_attachment=True,filename=f"{order.display_number}.pdf",content_type="application/pdf")
