from django.contrib import admin

from .models import (
    Brand,
    Category,
    Inventory,
    InventoryReservation,
    InventoryTransaction,
    Product,
    StockDocument,
    StockDocumentItem,
    UnitOfMeasure,
)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_active')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'parent', 'is_active')
    list_filter = ('parent',)


@admin.register(UnitOfMeasure)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'brand', 'category', 'unit', 'price', 'reorder_point', 'is_active')
    list_filter = ('brand', 'category', 'is_active')
    search_fields = ('sku', 'name', 'barcode')


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'warehouse', 'physical_qty', 'reserved_qty', 'in_transit_qty', 'available_qty')
    list_filter = ('warehouse',)
    search_fields = ('product__sku', 'product__name')

    def available_qty(self, obj):
        return obj.available_qty
    available_qty.short_description = 'قابل فروش'


@admin.register(InventoryTransaction)
class TxnAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'product', 'warehouse', 'type', 'qty', 'balance_after', 'reference')
    list_filter = ('type', 'warehouse')
    search_fields = ('reference', 'product__sku')


@admin.register(InventoryReservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'product', 'warehouse', 'qty', 'status', 'expires_at')
    list_filter = ('status', 'warehouse')
    search_fields = ('invoice_ref', 'product__sku')


class StockItemInline(admin.TabularInline):
    model = StockDocumentItem
    extra = 0


@admin.register(StockDocument)
class StockDocumentAdmin(admin.ModelAdmin):
    list_display = ('number', 'type', 'status', 'date', 'source_warehouse', 'dest_warehouse')
    list_filter = ('type', 'status')
    search_fields = ('number', 'note')
    inlines = [StockItemInline]
