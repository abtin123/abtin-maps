from decimal import Decimal
import csv
from django.db import models, transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.accounts.permissions import HasPermissionCode
from .models import Account, JournalEntry, JournalLine, Receipt, Cheque, FinancialDocument, Payroll, Commission, SalesTarget
from .serializers import (
    AccountSerializer, JournalEntrySerializer, JournalLineSerializer, ReceiptSerializer, ChequeSerializer,
    FinancialDocumentSerializer, PayrollSerializer, CommissionSerializer, SalesTargetSerializer,
)


class FinanceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasPermissionCode]
    permission_map = {'list': 'accounting.view', 'retrieve': 'accounting.view', 'create': 'accounting.manage', 'update': 'accounting.manage', 'partial_update': 'accounting.manage', 'destroy': 'accounting.manage'}
    def get_permissions(self):
        self.required_permission = self.permission_map.get(self.action, 'accounting.view')
        return super().get_permissions()

    def destroy(self, request, *args, **kwargs):
        return Response({'detail': 'حذف واقعی رکوردهای مالی مجاز نیست؛ سند را Void کنید.'}, status=405)


class AccountViewSet(FinanceViewSet):
    queryset = Account.objects.select_related('parent')
    serializer_class = AccountSerializer


class JournalEntryViewSet(FinanceViewSet):
    queryset = JournalEntry.objects.prefetch_related('lines__account').select_related('created_by')
    serializer_class = JournalEntrySerializer
    permission_map = {**FinanceViewSet.permission_map, 'post': 'accounting.manage', 'void': 'accounting.manage'}

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def post(self, request, pk=None):
        entry = JournalEntry.objects.select_for_update().get(pk=pk)
        if entry.status != JournalEntry.DRAFT:
            return Response({'detail': 'فقط سند پیش‌نویس قابل ثبت نهایی است.'}, status=400)
        totals = entry.lines.aggregate(debit_sum=models.Sum('debit'), credit_sum=models.Sum('credit'))
        debit = totals['debit_sum'] or Decimal('0'); credit = totals['credit_sum'] or Decimal('0')
        if debit <= 0 or debit != credit:
            return Response({'detail': 'سند باید حداقل یک مبلغ داشته و بدهکار و بستانکار برابر باشند.'}, status=400)
        if entry.lines.filter(debit__gt=0, credit__gt=0).exists() or entry.lines.filter(debit=0, credit=0).exists():
            return Response({'detail': 'هر خط باید دقیقاً یک طرف بدهکار یا بستانکار داشته باشد.'}, status=400)
        entry.status = JournalEntry.POSTED; entry.posted_at = timezone.now(); entry.save(update_fields=['status', 'posted_at'])
        return Response(self.get_serializer(entry).data)

    @action(detail=True, methods=['post'])
    def void(self, request, pk=None):
        entry = self.get_object()
        if entry.status != JournalEntry.POSTED:
            return Response({'detail': 'فقط سند ثبت‌شده قابل ابطال است.'}, status=400)
        entry.status = JournalEntry.VOID
        entry.save(update_fields=['status'])
        return Response(self.get_serializer(entry).data)


class JournalLineViewSet(FinanceViewSet):
    queryset = JournalLine.objects.select_related('entry', 'account')
    serializer_class = JournalLineSerializer
    permission_map = {**FinanceViewSet.permission_map, 'create': 'accounting.entry'}


class ReceiptViewSet(FinanceViewSet):
    queryset = Receipt.objects.select_related('invoice', 'customer', 'received_by')
    serializer_class = ReceiptSerializer
    permission_map = {**FinanceViewSet.permission_map, 'create': 'payments.receive'}
    def perform_create(self, serializer): serializer.save(received_by=self.request.user)


class ChequeViewSet(FinanceViewSet):
    queryset = Cheque.objects.select_related('receipt')
    serializer_class = ChequeSerializer
    permission_map = {'list': 'checks.view', 'retrieve': 'checks.view', 'create': 'checks.manage', 'update': 'checks.manage', 'partial_update': 'checks.manage', 'destroy': 'checks.manage', 'due': 'checks.view'}

    @action(detail=False, methods=['get'])
    def due(self, request):
        days = int(request.query_params.get('days', 7))
        return Response(self.get_serializer(self.get_queryset().due(days), many=True).data)


class FinancialDocumentViewSet(FinanceViewSet):
    queryset = FinancialDocument.objects.select_related('account', 'cash_account', 'journal_entry')
    serializer_class = FinancialDocumentSerializer

    def perform_create(self, serializer):
        document = serializer.save(created_by=self.request.user)
        with transaction.atomic():
            entry = JournalEntry.objects.create(number=f'AUTO-{document.number}', entry_date=document.document_date, description=document.title, reference=document.number, created_by=self.request.user)
            if document.document_type == FinancialDocument.INCOME:
                JournalLine.objects.create(entry=entry, account=document.cash_account, debit=document.amount)
                JournalLine.objects.create(entry=entry, account=document.account, credit=document.amount)
            else:
                JournalLine.objects.create(entry=entry, account=document.account, debit=document.amount)
                JournalLine.objects.create(entry=entry, account=document.cash_account, credit=document.amount)
            entry.status = JournalEntry.POSTED; entry.posted_at = timezone.now(); entry.save(update_fields=['status','posted_at'])
            document.journal_entry = entry
            document.save(update_fields=['journal_entry'])


class PayrollViewSet(FinanceViewSet):
    queryset = Payroll.objects.select_related('employee', 'created_by')
    serializer_class = PayrollSerializer
    permission_map = {**FinanceViewSet.permission_map, 'create': 'hr.payroll', 'update': 'hr.payroll', 'partial_update': 'hr.payroll'}
    def perform_create(self, serializer): serializer.save(created_by=self.request.user)


class CommissionViewSet(FinanceViewSet):
    queryset = Commission.objects.select_related('employee', 'created_by')
    serializer_class = CommissionSerializer
    permission_map = {**FinanceViewSet.permission_map, 'create': 'sales.commission', 'update': 'sales.commission', 'partial_update': 'sales.commission'}
    def perform_create(self, serializer): serializer.save(created_by=self.request.user)


class SalesTargetViewSet(FinanceViewSet):
    queryset = SalesTarget.objects.select_related('employee', 'branch', 'created_by')
    serializer_class = SalesTargetSerializer
    permission_map = {**FinanceViewSet.permission_map, 'create': 'sales.target_manage', 'update': 'sales.target_manage', 'partial_update': 'sales.target_manage'}
    def perform_create(self, serializer): serializer.save(created_by=self.request.user)


class FinanceReportView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, HasPermissionCode]
    required_permission = 'reports.view'

    @action(detail=False, methods=['get'])
    def summary(self, request):
        posted = JournalEntry.objects.filter(status=JournalEntry.POSTED)
        totals = JournalLine.objects.filter(entry__in=posted).aggregate(
            debit=models.Sum('debit'), credit=models.Sum('credit'))
        income = FinancialDocument.objects.filter(document_type=FinancialDocument.INCOME, is_void=False).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
        expense = FinancialDocument.objects.filter(document_type=FinancialDocument.EXPENSE, is_void=False).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
        return Response({
            'posted_debit': totals['debit'] or Decimal('0'),
            'posted_credit': totals['credit'] or Decimal('0'),
            'income': income,
            'expense': expense,
            'net_profit': income - expense,
            'due_cheques': Cheque.objects.due(7).count(),
        })

    @action(detail=False, methods=['get'], url_path='csv')
    def csv(self, request):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="finance-journal.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(['شماره سند', 'تاریخ', 'شرح', 'وضعیت', 'جمع بدهکار', 'جمع بستانکار'])
        for entry in JournalEntry.objects.filter(status=JournalEntry.POSTED).prefetch_related('lines').order_by('-entry_date'):
            debit = sum((line.debit for line in entry.lines.all()), Decimal('0'))
            credit = sum((line.credit for line in entry.lines.all()), Decimal('0'))
            writer.writerow([entry.number, entry.entry_date, entry.description, entry.status, debit, credit])
        return response
