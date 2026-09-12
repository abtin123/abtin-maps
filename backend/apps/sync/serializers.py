from rest_framework import serializers
from .models import SyncOperation

class SyncOperationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncOperation
        fields = '__all__'
        read_only_fields = ('user', 'server_updated_at', 'status', 'error')
