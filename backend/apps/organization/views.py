from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import HasPermissionCode

from .models import Branch, City, Company, Warehouse, Zone
from .serializers import (
    BranchSerializer,
    CitySerializer,
    CompanySerializer,
    WarehouseSerializer,
    ZoneSerializer,
)


class _PermViewSet(viewsets.ModelViewSet):
    """CRUD کامل با گارد Permission نقش‌محور."""
    permission_classes = [IsAuthenticated, HasPermissionCode]
    required_permission = 'settings.manage'  # ویرایش سازمان = مدیر سیستم / مدیر کل
    # اجازه خواندن با view روی لیست/جزء (override در متد)

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            self.required_permission = 'settings.view'
        else:
            self.required_permission = 'settings.manage'
        return super().get_permissions()


class CompanyViewSet(_PermViewSet):
    queryset = Company.objects.all().order_by('code')
    serializer_class = CompanySerializer
    search_fields = ('code', 'name', 'national_id')
    filterset_fields = ('is_active',)


class BranchViewSet(_PermViewSet):
    queryset = Branch.objects.select_related('company').order_by('company', 'code')
    serializer_class = BranchSerializer
    search_fields = ('code', 'name', 'manager_name')
    filterset_fields = ('company', 'is_active')


class WarehouseViewSet(_PermViewSet):
    queryset = Warehouse.objects.select_related('branch').order_by('branch', 'code')
    serializer_class = WarehouseSerializer
    search_fields = ('code', 'name', 'keeper_name')
    filterset_fields = ('branch', 'type', 'is_active')


class ZoneViewSet(_PermViewSet):
    queryset = Zone.objects.select_related('branch').order_by('branch', 'code')
    serializer_class = ZoneSerializer
    search_fields = ('code', 'name')
    filterset_fields = ('branch', 'is_active')


class CityViewSet(_PermViewSet):
    queryset = City.objects.select_related('zone').order_by('zone', 'name')
    serializer_class = CitySerializer
    search_fields = ('name', 'province')
    filterset_fields = ('zone', 'province')
