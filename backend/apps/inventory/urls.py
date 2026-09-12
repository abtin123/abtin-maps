from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    BrandViewSet,
    CategoryViewSet,
    ConvertReservationView,
    InventoryTransactionViewSet,
    InventoryViewSet,
    ProductViewSet,
    ReleaseReservationView,
    ReservationViewSet,
    ReserveStockView,
    StockDocumentViewSet,
    UnitViewSet,
)

app_name = 'inventory'

router = DefaultRouter()
router.register('brands', BrandViewSet, basename='brand')
router.register('categories', CategoryViewSet, basename='category')
router.register('units', UnitViewSet, basename='unit')
router.register('products', ProductViewSet, basename='product')
router.register('stocks', InventoryViewSet, basename='stock')
router.register('transactions', InventoryTransactionViewSet, basename='transaction')
router.register('reservations', ReservationViewSet, basename='reservation')
router.register('documents', StockDocumentViewSet, basename='document')

urlpatterns = router.urls + [
    path('reserve/', ReserveStockView.as_view(), name='reserve'),
    path('reservations/<int:pk>/release/', ReleaseReservationView.as_view(), name='reservation-release'),
    path('reservations/<int:pk>/convert/', ConvertReservationView.as_view(), name='reservation-convert'),
]
