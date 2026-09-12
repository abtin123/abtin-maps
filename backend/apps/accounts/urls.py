from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    LoginView,
    LogoutView,
    OTPRequestView,
    OTPVerifyView,
    PermissionListView,
    ProfileView,
    RoleListView,
    SwitchRoleView,
)

app_name = 'accounts'

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('otp/request/', OTPRequestView.as_view(), name='otp_request'),
    path('otp/verify/', OTPVerifyView.as_view(), name='otp_verify'),
    path('me/', ProfileView.as_view(), name='profile'),
    path('switch-role/', SwitchRoleView.as_view(), name='switch_role'),
    path('roles/', RoleListView.as_view(), name='roles'),
    path('permissions/', PermissionListView.as_view(), name='permissions'),
]
