from rest_framework.routers import DefaultRouter
from .views import SyncOperationViewSet

router = DefaultRouter()
router.register('operations', SyncOperationViewSet, basename='sync-operations')
urlpatterns = router.urls
