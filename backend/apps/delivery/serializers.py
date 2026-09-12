from rest_framework import serializers
from .models import Route, RouteStop, Visit, GPSTrack, Vehicle, DeliveryTrip, DeliveryStop, DeliveryAttempt

class RouteStopSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    class Meta:
        model = RouteStop
        fields = '__all__'

class RouteSerializer(serializers.ModelSerializer):
    stops = RouteStopSerializer(many=True, required=False)
    class Meta:
        model = Route
        fields = '__all__'
        read_only_fields = ('sales_rep',)
    def create(self, validated_data):
        stops = validated_data.pop('stops', [])
        route = Route.objects.create(sales_rep=self.context['request'].user, **validated_data)
        for stop in stops: RouteStop.objects.create(route=route, **stop)
        return route

class RoutePlanSerializer(serializers.Serializer):
    points = serializers.ListField(child=serializers.JSONField(), required=False, default=list)
    track = serializers.ListField(child=serializers.ListField(child=serializers.FloatField()), required=False, default=list)
    distance = serializers.FloatField(required=False, min_value=0, default=0)
    duration = serializers.FloatField(required=False, min_value=0, default=0)
    optimized = serializers.BooleanField(required=False, default=False)
    steps = serializers.ListField(child=serializers.JSONField(), required=False, default=list)

class VisitSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='route_stop.customer.name', read_only=True)
    customer_latitude = serializers.DecimalField(source='route_stop.customer.latitude', max_digits=9, decimal_places=6, read_only=True)
    customer_longitude = serializers.DecimalField(source='route_stop.customer.longitude', max_digits=9, decimal_places=6, read_only=True)
    class Meta:
        model = Visit
        fields = ('id', 'route_stop', 'user', 'visit_date', 'status', 'check_in_at', 'check_out_at', 'check_in_latitude', 'check_in_longitude', 'check_out_latitude', 'check_out_longitude', 'note', 'customer_name', 'customer_latitude', 'customer_longitude')
        read_only_fields = ('user', 'status', 'check_in_at', 'check_out_at')

class GPSTrackSerializer(serializers.ModelSerializer):
    class Meta:
        model = GPSTrack
        fields = '__all__'
        read_only_fields = ('user',)

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = '__all__'

class DeliveryStopSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(source='invoice.number', read_only=True)
    customer_name = serializers.CharField(source='invoice.customer_name_snapshot', read_only=True)
    customer_address = serializers.CharField(source='invoice.customer_address_snapshot', read_only=True)
    customer_latitude = serializers.DecimalField(source='invoice.customer_latitude_snapshot', max_digits=9, decimal_places=6, read_only=True)
    customer_longitude = serializers.DecimalField(source='invoice.customer_longitude_snapshot', max_digits=9, decimal_places=6, read_only=True)
    invoice_status = serializers.CharField(source='invoice.status', read_only=True)
    invoice_total = serializers.DecimalField(source='invoice.total', max_digits=16, decimal_places=0, read_only=True)
    invoice_items = serializers.SerializerMethodField()

    def get_invoice_items(self, obj):
        return [{'product': item.product_id, 'product_name': item.product.name, 'qty': item.qty, 'unit_price': item.unit_price, 'line_total': item.line_total} for item in obj.invoice.items.select_related('product').all()]

    class Meta:
        model = DeliveryStop
        fields = '__all__'

class DeliveryTripSerializer(serializers.ModelSerializer):
    stops = DeliveryStopSerializer(many=True, required=False)
    class Meta:
        model = DeliveryTrip
        fields = '__all__'
    def create(self, validated_data):
        stops = validated_data.pop('stops', [])
        trip = DeliveryTrip.objects.create(**validated_data)
        for stop in stops: DeliveryStop.objects.create(trip=trip, **stop)
        return trip

class DeliveryAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryAttempt
        fields = '__all__'
        read_only_fields = ('recorded_by', 'created_at')

class DeliveryActionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=DeliveryAttempt.STATUSES)
    reason = serializers.ChoiceField(choices=DeliveryAttempt.REASONS, required=False, allow_blank=True, default='')
    delivered_qty = serializers.JSONField(required=False, default=dict)
    received_amount = serializers.DecimalField(max_digits=16, decimal_places=0, min_value=0, required=False, default=0)
    payment_method = serializers.CharField(required=False, allow_blank=True, default='')
    signature_url = serializers.URLField(required=False, allow_blank=True, default='')
    photo_url = serializers.URLField(required=False, allow_blank=True, default='')
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True, default=None)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True, default=None)
    note = serializers.CharField(required=False, allow_blank=True, default='')
