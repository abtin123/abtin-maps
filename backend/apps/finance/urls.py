from rest_framework.routers import DefaultRouter
from .views import (
    AccountViewSet, JournalEntryViewSet, JournalLineViewSet, ReceiptViewSet, ChequeViewSet,
    FinancialDocumentViewSet, PayrollViewSet, CommissionViewSet, SalesTargetViewSet, FinanceReportView,
)

router = DefaultRouter()
router.register('accounts', AccountViewSet)
router.register('journal-entries', JournalEntryViewSet)
router.register('journal-lines', JournalLineViewSet)
router.register('receipts', ReceiptViewSet)
router.register('cheques', ChequeViewSet)
router.register('financial-documents', FinancialDocumentViewSet)
router.register('payroll', PayrollViewSet)
router.register('commissions', CommissionViewSet)
router.register('targets', SalesTargetViewSet)
router.register('reports', FinanceReportView, basename='finance-reports')
urlpatterns = router.urls
