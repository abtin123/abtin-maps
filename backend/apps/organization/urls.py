from rest_framework.routers import DefaultRouter

from .views import BranchViewSet, CityViewSet, CompanyViewSet, WarehouseViewSet, ZoneViewSet

app_name = 'organization'

router = DefaultRouter()
router.register('companies', CompanyViewSet, basename='company')
router.register('branches', BranchViewSet, basename='branch')
router.register('warehouses', WarehouseViewSet, basename='warehouse')
router.register('zones', ZoneViewSet, basename='zone')
router.register('cities', CityViewSet, basename='city')

urlpatterns = router.urls
