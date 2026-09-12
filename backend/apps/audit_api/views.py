from auditlog.models import LogEntry
from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from apps.accounts.permissions import HasPermissionCode

class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.full_name', read_only=True)
    class Meta:
        model = LogEntry
        fields = ('id', 'actor', 'actor_name', 'action', 'object_pk', 'object_repr', 'timestamp', 'changes', 'remote_addr')

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, HasPermissionCode]
    required_permission = 'audit.view'
    queryset = LogEntry.objects.select_related('actor').order_by('-timestamp')
