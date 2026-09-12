from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import CustomerViewSet, PriceLevelViewSet, ProductPriceViewSet, CampaignViewSet, InvoiceViewSet, InvoiceHistoryViewSet, ApprovalViewSet, PaymentViewSet
router = DefaultRouter()
router.register('customers', CustomerViewSet)
router.register('price-levels', PriceLevelViewSet)
router.register('product-prices', ProductPriceViewSet)
router.register('campaigns', CampaignViewSet)
router.register('invoices', InvoiceViewSet)
router.register('invoice-history', InvoiceHistoryViewSet)
router.register('approvals', ApprovalViewSet)
router.register('payments', PaymentViewSet)
urlpatterns = [path('', include(router.urls))]
