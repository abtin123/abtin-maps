from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.accounts.permissions import HasPermissionCode
from .models import Customer, PriceLevel, ProductPrice, Campaign, Invoice, InvoiceStatusHistory, ApprovalRequest, Payment
from .serializers import *
from .services import create_invoice, transition_invoice, reserve_invoice, confirm_invoice, cancel_invoice, record_payment

class SalesPermissionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasPermissionCode]
    permission_map = {'list': 'invoices.view', 'retrieve': 'invoices.view', 'create': 'invoices.create', 'update': 'invoices.create', 'partial_update': 'invoices.create', 'destroy': 'invoices.cancel'}
    def get_permissions(self):
        self.required_permission = self.permission_map.get(self.action, 'invoices.view')
        return super().get_permissions()

class CustomerViewSet(SalesPermissionViewSet):
    queryset = Customer.objects.select_related('price_level')
    serializer_class = CustomerSerializer
    permission_map = {'list': 'customers.view', 'retrieve': 'customers.view', 'create': 'customers.create', 'update': 'customers.edit', 'partial_update': 'customers.edit', 'destroy': 'customers.edit'}
    search_fields = ('code', 'name', 'mobile')

class PriceLevelViewSet(SalesPermissionViewSet):
    queryset = PriceLevel.objects.all()
    serializer_class = PriceLevelSerializer
    permission_map = {'list': 'products.view', 'retrieve': 'products.view', 'create': 'products.edit', 'update': 'products.edit', 'partial_update': 'products.edit', 'destroy': 'products.edit'}

class ProductPriceViewSet(PriceLevelViewSet):
    queryset = ProductPrice.objects.select_related('product', 'price_level')
    serializer_class = ProductPriceSerializer

class CampaignViewSet(SalesPermissionViewSet):
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer
    permission_map = {'list': 'sales.campaign', 'retrieve': 'sales.campaign', 'create': 'sales.campaign', 'update': 'sales.campaign', 'partial_update': 'sales.campaign', 'destroy': 'sales.campaign'}

class InvoiceViewSet(SalesPermissionViewSet):
    queryset = Invoice.objects.select_related('customer', 'warehouse', 'seller').prefetch_related('items__product', 'status_history', 'payments', 'reservations')
    serializer_class = InvoiceSerializer
    search_fields = ('number', 'customer__name', 'customer__code')
    filterset_fields = ('status', 'customer', 'warehouse', 'seller')
    permission_map = {
        'list': 'invoices.view', 'retrieve': 'invoices.view',
        'create': 'invoices.create', 'update': 'invoices.create',
        'partial_update': 'invoices.create', 'destroy': 'invoices.cancel',
        'submit': 'invoices.create', 'approve': 'invoices.confirm',
        'reserve': 'inventory.reserve_manage', 'confirm': 'invoices.confirm',
        'cancel': 'invoices.cancel',
    }

    def destroy(self, request, *args, **kwargs):
        return Response({'detail': 'حذف فاکتور مجاز نیست؛ از لغو فاکتور و ثبت تاریخچه استفاده کنید.'}, status=405)

    def perform_create(self, serializer):
        data = serializer.validated_data
        items = data.pop('items', [])
        data['items'] = items
        invoice = create_invoice(data=data, user=self.request.user)
        serializer.instance = invoice

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        invoice = self.get_object()
        try:
            transition_invoice(invoice, Invoice.STATUS_PENDING_APPROVAL, request.user, request.data.get('note', ''))
            if invoice.credit_approval_required:
                ApprovalRequest.objects.get_or_create(invoice=invoice, type=ApprovalRequest.TYPE_CREDIT)
            if invoice.discount_total:
                ApprovalRequest.objects.get_or_create(invoice=invoice, type=ApprovalRequest.TYPE_DISCOUNT)
        except ValidationError as exc:
            return Response({'detail': str(exc)}, status=400)
        return Response(self.get_serializer(invoice).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        invoice = self.get_object()
        try:
            transition_invoice(invoice, Invoice.STATUS_APPROVED, request.user, request.data.get('note', ''))
        except ValidationError as exc:
            return Response({'detail': str(exc)}, status=400)
        return Response(self.get_serializer(invoice).data)

    @action(detail=True, methods=['post'])
    def reserve(self, request, pk=None):
        invoice = self.get_object()
        try: reserve_invoice(invoice, request.user)
        except ValidationError as exc:
            return Response({'detail': str(exc)}, status=400)
        return Response(self.get_serializer(invoice).data)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        invoice = self.get_object()
        try: confirm_invoice(invoice, request.user)
        except ValidationError as exc: return Response({'detail': str(exc)}, status=400)
        return Response(self.get_serializer(invoice).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        invoice = self.get_object()
        try: cancel_invoice(invoice, request.user, request.data.get('note', 'لغو فاکتور'))
        except ValidationError as exc: return Response({'detail': str(exc)}, status=400)
        return Response(self.get_serializer(invoice).data)

    def _transition(self, request, pk, target):
        invoice = self.get_object()
        try: transition_invoice(invoice, target, request.user, request.data.get('note', ''))
        except ValidationError as exc: return Response({'detail': str(exc)}, status=400)
        return Response(self.get_serializer(invoice).data)

class InvoiceHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InvoiceStatusHistory.objects.select_related('invoice', 'changed_by')
    serializer_class = InvoiceStatusHistorySerializer
    permission_classes = [IsAuthenticated, HasPermissionCode]
    required_permission = 'invoices.view'
    filterset_fields = ('invoice', 'to_status')

class ApprovalViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ApprovalRequest.objects.select_related('invoice', 'decided_by')
    serializer_class = ApprovalRequestSerializer
    permission_classes = [IsAuthenticated, HasPermissionCode]
    required_permission = 'approvals.view'
    filterset_fields = ('invoice', 'type', 'status')

    @action(detail=True, methods=['post'])
    def decide(self, request, pk=None):
        if not request.user.has_perm_code('approvals.decide'):
            return Response({'detail': 'مجوز تصمیم‌گیری ندارید.'}, status=403)
        obj = self.get_object()
        decision = request.data.get('decision')
        if decision not in (ApprovalRequest.STATUS_APPROVED, ApprovalRequest.STATUS_REJECTED): return Response({'detail': 'decision نامعتبر است.'}, status=400)
        obj.status, obj.decided_by, obj.decided_at = decision, request.user, timezone.now()
        obj.save(update_fields=['status', 'decided_by', 'decided_at'])
        return Response(self.get_serializer(obj).data)

class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payment.objects.select_related('invoice', 'received_by')
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated, HasPermissionCode]
    required_permission = 'payments.receive'
    filterset_fields = ('invoice', 'method')

    @action(detail=False, methods=['post'])
    def receive(self, request):
        s = PaymentActionSerializer(data=request.data); s.is_valid(raise_exception=True)
        invoice = get_object_or_404(Invoice, pk=request.data.get('invoice'))
        try: payment = record_payment(invoice, user=request.user, **s.validated_data)
        except ValidationError as exc: return Response({'detail': str(exc)}, status=400)
        return Response(PaymentSerializer(payment).data, status=201)
