from rest_framework import serializers
from .models import Customer, PriceLevel, ProductPrice, Campaign, Invoice, InvoiceItem, InvoiceStatusHistory, ApprovalRequest, Payment

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'

class PriceLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceLevel
        fields = '__all__'

class ProductPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPrice
        fields = '__all__'

class CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = '__all__'

class InvoiceItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    class Meta:
        model = InvoiceItem
        fields = ('id', 'product', 'product_name', 'warehouse', 'qty', 'unit_price', 'discount_percent', 'discount_amount', 'tax_amount', 'line_total')
        read_only_fields = ('warehouse', 'discount_amount', 'tax_amount', 'line_total')
        extra_kwargs = {'unit_price': {'required': False, 'allow_null': True}}

class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, required=False)
    balance = serializers.DecimalField(max_digits=16, decimal_places=0, read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    class Meta:
        model = Invoice
        fields = ('id', 'number', 'customer', 'customer_name', 'warehouse', 'seller', 'status', 'status_label', 'items', 'customer_name_snapshot', 'customer_address_snapshot', 'customer_latitude_snapshot', 'customer_longitude_snapshot', 'subtotal', 'discount_total', 'tax_total', 'total', 'paid_total', 'balance', 'payment_status', 'credit_approval_required', 'created_at', 'updated_at')
        read_only_fields = ('seller', 'status', 'payment_status', 'customer_name_snapshot', 'customer_address_snapshot', 'customer_latitude_snapshot', 'customer_longitude_snapshot', 'subtotal', 'discount_total', 'tax_total', 'total', 'paid_total', 'credit_approval_required')

class InvoiceStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceStatusHistory
        fields = '__all__'

class ApprovalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalRequest
        fields = '__all__'
        read_only_fields = ('status', 'decided_by', 'decided_at')

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ('received_by', 'received_at')

class InvoiceActionSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default='')

class PaymentActionSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=Payment.METHODS)
    amount = serializers.DecimalField(max_digits=16, decimal_places=0, min_value=1)
    reference = serializers.CharField(required=False, allow_blank=True, default='')
