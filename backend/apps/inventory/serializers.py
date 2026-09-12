from rest_framework import serializers

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


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ('id', 'code', 'name', 'is_active')


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'code', 'name', 'parent', 'is_active')


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitOfMeasure
        fields = ('id', 'code', 'name')


class ProductSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    unit_name = serializers.CharField(source='unit.name', read_only=True)

    class Meta:
        model = Product
        fields = (
            'id', 'sku', 'barcode', 'name', 'brand', 'brand_name',
            'category', 'category_name', 'unit', 'unit_name',
            'pack_size', 'weight_grams', 'price', 'tax_rate',
            'reorder_point', 'has_expiry', 'is_active', 'created_at',
        )


class InventorySerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    warehouse_code = serializers.CharField(source='warehouse.code', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    available_qty = serializers.IntegerField(read_only=True)
    below_reorder = serializers.SerializerMethodField()

    class Meta:
        model = Inventory
        fields = (
            'id', 'product', 'product_sku', 'product_name',
            'warehouse', 'warehouse_code', 'warehouse_name',
            'physical_qty', 'reserved_qty', 'in_transit_qty', 'available_qty',
            'avg_cost', 'below_reorder', 'updated_at',
        )

    def get_below_reorder(self, obj):
        return obj.available_qty <= (obj.product.reorder_point or 0)


class InventoryTransactionSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    warehouse_code = serializers.CharField(source='warehouse.code', read_only=True)
    type_label = serializers.CharField(source='get_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = InventoryTransaction
        fields = (
            'id', 'product', 'product_sku', 'warehouse', 'warehouse_code',
            'type', 'type_label', 'qty', 'balance_after', 'unit_cost',
            'reference', 'note', 'created_by', 'created_by_name', 'created_at',
        )


class InventoryReservationSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    warehouse_code = serializers.CharField(source='warehouse.code', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = InventoryReservation
        fields = (
            'id', 'product', 'product_sku', 'warehouse', 'warehouse_code',
            'qty', 'invoice_ref', 'status', 'status_label', 'expires_at',
            'created_by', 'created_at', 'released_at',
        )


class ReserveActionSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.filter(is_active=True))
    warehouse = serializers.IntegerField()
    qty = serializers.IntegerField(min_value=1)
    invoice_ref = serializers.CharField(required=False, allow_blank=True, default='')


class StockDocumentItemSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source='product.sku', read_only=True)

    class Meta:
        model = StockDocumentItem
        fields = ('id', 'product', 'product_sku', 'qty', 'unit_cost', 'note')


class StockDocumentSerializer(serializers.ModelSerializer):
    items = StockDocumentItemSerializer(many=True)
    type_label = serializers.CharField(source='get_type_display', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = StockDocument
        fields = (
            'id', 'number', 'type', 'type_label', 'status', 'status_label',
            'date', 'source_warehouse', 'dest_warehouse', 'note',
            'items', 'created_by', 'posted_by', 'created_at', 'posted_at',
        )
        read_only_fields = ('status', 'created_by', 'posted_by', 'posted_at')

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        request = self.context.get('request')
        validated_data['created_by'] = request.user
        doc = StockDocument.objects.create(**validated_data)
        for item in items_data:
            StockDocumentItem.objects.create(document=doc, **item)
        return doc
