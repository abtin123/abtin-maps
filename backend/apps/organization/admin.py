from django.contrib import admin

from .models import Branch, City, Company, Warehouse, Zone


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'phone', 'is_active')
    search_fields = ('code', 'name', 'national_id')


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'company', 'manager_name', 'is_active')
    list_filter = ('company', 'is_active')
    search_fields = ('code', 'name')


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'branch', 'type', 'is_active')
    list_filter = ('branch', 'type', 'is_active')
    search_fields = ('code', 'name')


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'branch', 'is_active')
    list_filter = ('branch', 'is_active')


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'zone', 'province', 'postal_prefix')
    list_filter = ('province',)
    search_fields = ('name',)
