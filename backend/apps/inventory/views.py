from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasPermissionCode
from apps.organization.models import Warehouse

from .models import (
    Brand,
    Category,
    Inventory,
    InventoryReservation,
    InventoryTransaction,
    Product,
    StockDocument,
    UnitOfMeasure,
)
from .serializers import (
    BrandSerializer,
    CategorySerializer,
    InventoryReservationSerializer,
    InventorySerializer,
    InventoryTransactionSerializer,
    ProductSerializer,
    ReserveActionSerializer,
    StockDocumentSerializer,
    UnitSerializer,
)
from .services import (
    InsufficientStock,
    convert_reservation_to_out,
    post_stock_document,
    release_reservation,
    reserve_stock,
)


class _PermViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasPermissionCode]
    view_perm = 'products.view'
    edit_perm = 'products.edit'
    create_perm = 'products.create'
    delete_perm = 'products.delete'

    def get_permissions(self):
        m = {
            'list': self.view_perm, 'retrieve': self.view_perm,
            'create': self.create_perm, 'update': self.edit_perm,
            'partial_update': self.edit_perm, 'destroy': self.delete_perm,
        }
        self.required_permission = m.get(self.action, self.view_perm)
        return super().get_permissions()


# ---------------- CRUD کالا و طبقه‌بندی ----------------
class BrandViewSet(_PermViewSet):
    queryset = Brand.objects.all().order_by('name')
    serializer_class = BrandSerializer
    search_fields = ('code', 'name')
    filterset_fields = ('is_active',)


class CategoryViewSet(_PermViewSet):
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    search_fields = ('code', 'name')
    filterset_fields = ('parent', 'is_active')


class UnitViewSet(_PermViewSet):
    queryset = UnitOfMeasure.objects.all().order_by('code')
    serializer_class = UnitSerializer


class ProductViewSet(_PermViewSet):
    queryset = Product.objects.select_related('brand', 'category', 'unit').order_by('sku')
    serializer_class = ProductSerializer
    search_fields = ('sku', 'name', 'barcode')
    filterset_fields = ('brand', 'category', 'is_active', 'has_expiry')

    @action(detail=False, methods=['get'], url_path='by-barcode/(?P<barcode>[^/]+)')
    def by_barcode(self, request, barcode=None):
        """جستجوی سریع بارکد برای فرم‌های فروش/انبار."""
        product = get_object_or_404(Product, barcode=barcode, is_active=True)
        return Response(self.get_serializer(product).data)


# ---------------- موجودی و کاردکس ----------------
class InventoryViewSet(viewsets.ReadOnlyModelViewSet):
    """موجودی لحظه‌ای — read-only؛ تغییرات فقط از طریق StockDocument."""
    queryset = Inventory.objects.select_related('product', 'warehouse').order_by('warehouse', 'product')
    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticated, HasPermissionCode]
    required_permission = 'inventory.view'
    search_fields = ('product__sku', 'product__name', 'product__barcode')
    filterset_fields = ('warehouse', 'product')

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """کالاهایی که available_qty ≤ reorder_point (هشدار نقطه سفارش)."""
        rows = [
            self.get_serializer(inv).data
            for inv in self.get_queryset()
            if inv.available_qty <= (inv.product.reorder_point or 0)
        ]
        return Response(rows)


class InventoryTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """کاردکس / گردش کالا — read-only."""
    queryset = InventoryTransaction.objects.select_related('product', 'warehouse', 'created_by')
    serializer_class = InventoryTransactionSerializer
    permission_classes = [IsAuthenticated, HasPermissionCode]
    required_permission = 'inventory.view'
    filterset_fields = ('product', 'warehouse', 'type', 'created_by')
    ordering = ('-created_at',)


# ---------------- رزرو موجودی ----------------
class ReservationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InventoryReservation.objects.select_related('product', 'warehouse', 'created_by')
    serializer_class = InventoryReservationSerializer
    permission_classes = [IsAuthenticated, HasPermissionCode]
    required_permission = 'inventory.view'
    filterset_fields = ('product', 'warehouse', 'status')


class ReserveStockView(APIView):
    """POST /api/inventory/reserve/ — رزرو تراکنشی (Race-Condition Safe)."""
    permission_classes = [IsAuthenticated, HasPermissionCode]
    required_permission = 'inventory.reserve_manage'

    def post(self, request):
        s = ReserveActionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        warehouse = get_object_or_404(Warehouse, pk=s.validated_data['warehouse'])
        try:
            reservation = reserve_stock(
                product=s.validated_data['product'],
                warehouse=warehouse,
                qty=s.validated_data['qty'],
                user=request.user,
                invoice_ref=s.validated_data.get('invoice_ref', ''),
            )
        except InsufficientStock as e:
            return Response({'detail': str(e)}, status=status.HTTP_409_CONFLICT)
        except ValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(InventoryReservationSerializer(reservation).data, status=201)


class ReleaseReservationView(APIView):
    """POST /api/inventory/reservations/<id>/release/"""
    permission_classes = [IsAuthenticated, HasPermissionCode]
    required_permission = 'inventory.reserve_manage'

    def post(self, request, pk):
        r = get_object_or_404(InventoryReservation, pk=pk)
        release_reservation(r)
        return Response(InventoryReservationSerializer(r).data)


class ConvertReservationView(APIView):
    """POST /api/inventory/reservations/<id>/convert/ — تبدیل به خروج فیزیکی."""
    permission_classes = [IsAuthenticated, HasPermissionCode]
    required_permission = 'inventory.reserve_manage'

    def post(self, request, pk):
        r = get_object_or_404(InventoryReservation, pk=pk)
        try:
            convert_reservation_to_out(r, request.user, reference=request.data.get('reference', ''))
        except (InsufficientStock, ValidationError) as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(InventoryReservationSerializer(r).data)


# ---------------- اسناد انبار ----------------
class StockDocumentViewSet(viewsets.ModelViewSet):
    queryset = StockDocument.objects.select_related(
        'source_warehouse', 'dest_warehouse', 'created_by', 'posted_by'
    ).prefetch_related('items__product').order_by('-date', '-id')
    serializer_class = StockDocumentSerializer
    permission_classes = [IsAuthenticated, HasPermissionCode]
    filterset_fields = ('type', 'status', 'source_warehouse', 'dest_warehouse')

    _perm_map = {
        'list': 'inventory.view', 'retrieve': 'inventory.view',
        'create': 'inventory.entry', 'update': 'inventory.entry',
        'partial_update': 'inventory.entry', 'destroy': 'inventory.entry',
        'post': 'inventory.entry',
    }

    def get_permissions(self):
        self.required_permission = self._perm_map.get(self.action, 'inventory.view')
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def post(self, request, pk=None):
        """ثبت نهایی سند → اعمال روی موجودی."""
        doc = self.get_object()
        try:
            post_stock_document(doc, request.user)
        except (InsufficientStock, ValidationError) as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(doc).data)
