from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # Domain apps (to be implemented in next phases)
    path('api/auth/', include('apps.accounts.urls')),
    path('api/org/', include('apps.organization.urls')),
    path('api/inventory/', include('apps.inventory.urls')),
    path('api/sales/', include('apps.sales.urls')),
    path('api/delivery/', include('apps.delivery.urls')),
    path('api/finance/', include('apps.finance.urls')),
    path('api/hr/', include('apps.hr.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/sync/', include('apps.sync.urls')),
    path('api/audit/', include('apps.audit_api.urls')),
]
