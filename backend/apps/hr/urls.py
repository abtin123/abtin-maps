from rest_framework.routers import DefaultRouter
from .views import EmployeeViewSet, AttendanceViewSet, LeaveRequestViewSet

router = DefaultRouter()
router.register('employees', EmployeeViewSet)
router.register('attendance', AttendanceViewSet)
router.register('leave-requests', LeaveRequestViewSet)
urlpatterns = router.urls
