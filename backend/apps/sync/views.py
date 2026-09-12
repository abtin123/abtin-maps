from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.accounts.permissions import HasPermissionCode
from .models import SyncOperation
from .serializers import SyncOperationSerializer

class SyncOperationViewSet(viewsets.GenericViewSet):
    serializer_class = SyncOperationSerializer
    permission_classes = [IsAuthenticated, HasPermissionCode]
    required_permission = 'orders.create'

    def get_queryset(self):
        return SyncOperation.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def push(self, request):
        operations = request.data if isinstance(request.data, list) else request.data.get('operations', [])
        accepted, conflicts = [], []
        for item in operations:
            client_id = item.get('client_id')
            if not client_id or not item.get('entity') or not item.get('operation'):
                conflicts.append({'client_id': client_id, 'error': 'client_id، entity و operation الزامی هستند.'})
                continue
            existing = self.get_queryset().filter(client_id=client_id).first()
            if existing:
                accepted.append(self.get_serializer(existing).data)
                continue
            try:
                operation = SyncOperation.objects.create(
                    client_id=client_id, user=request.user, entity=item['entity'],
                    operation=item['operation'], payload=item.get('payload', {}),
                    client_updated_at=item.get('client_updated_at'), status=SyncOperation.APPLIED,
                )
                accepted.append(self.get_serializer(operation).data)
            except IntegrityError:
                conflicts.append({'client_id': client_id, 'error': 'عملیات تکراری یا متعارض است.'})
        return Response({'accepted': accepted, 'conflicts': conflicts})

    @action(detail=False, methods=['get'])
    def pull(self, request):
        since = request.query_params.get('since')
        query = self.get_queryset().filter(status=SyncOperation.APPLIED)
        if since:
            query = query.filter(server_updated_at__gt=since)
        return Response(self.get_serializer(query[:500], many=True).data)
