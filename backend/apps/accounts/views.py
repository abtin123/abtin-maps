from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.exceptions import TokenError

from .models import Permission, Role
from .permissions import IsSuperAdmin
from .serializers import (
    LoginSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
    PermissionSerializer,
    RoleSerializer,
    SwitchRoleSerializer,
    UserSerializer,
)


class LoginView(APIView):
    """POST /api/auth/login/ — نام کاربری + رمز عبور → JWT"""
    permission_classes = [AllowAny]
    class LoginThrottle(AnonRateThrottle):
        scope = 'login'
    throttle_classes = [LoginThrottle]

    def post(self, request):
        s = LoginSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        return Response(s.save(), status=status.HTTP_200_OK)


class OTPRequestView(APIView):
    """POST /api/auth/otp/request/ — ارسال کد یک‌بارمصرف"""
    permission_classes = [AllowAny]

    class OTPThrottle(AnonRateThrottle):
        scope = 'otp'

    throttle_classes = [OTPThrottle]

    def post(self, request):
        s = OTPRequestSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        otp = s.save()
        # TODO: اتصال به سرویس SMS واقعی (کاوه‌نگار/پیامک‌نت) — فعلاً در dev کد برمی‌گردد
        payload = {'detail': 'کد تأیید ارسال شد', 'expires_in': 120}
        if settings.DEBUG:
            payload['dev_code'] = otp.code
        return Response(payload, status=status.HTTP_200_OK)


class OTPVerifyView(APIView):
    """POST /api/auth/otp/verify/ — تأیید کد → JWT"""
    permission_classes = [AllowAny]
    class OTPVerifyThrottle(AnonRateThrottle):
        scope = 'otp'
    throttle_classes = [OTPVerifyThrottle]

    def post(self, request):
        s = OTPVerifySerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        return Response(s.save(), status=status.HTTP_200_OK)


class ProfileView(APIView):
    """GET /api/auth/me/ — پروفایل کاربر جاری + نقش + مجوزها"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class SwitchRoleView(APIView):
    """POST /api/auth/switch-role/ — سوییچ نقش (فقط مدیر کل)"""
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        s = SwitchRoleSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        return Response(s.save(), status=status.HTTP_200_OK)


class RoleListView(APIView):
    """GET /api/auth/roles/ — لیست نقش‌ها و مجوزها (برای ماتریس دسترسی)"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(RoleSerializer(Role.objects.prefetch_related('permissions'), many=True).data)


class PermissionListView(APIView):
    """GET /api/auth/permissions/ — همه مجوزهای سیستم"""
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        return Response(PermissionSerializer(Permission.objects.all(), many=True).data)


class LogoutView(APIView):
    """POST /api/auth/logout/ — Blacklist کردن refresh token"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from rest_framework_simplejwt.tokens import RefreshToken
        try:
            RefreshToken(request.data.get('refresh')).blacklist()
        except (TokenError, TypeError, ValueError):
            # Logout is idempotent: an expired or already-blacklisted token is harmless.
            return Response({'detail': 'خروج موفق'}, status=status.HTTP_200_OK)
        return Response({'detail': 'خروج موفق'}, status=status.HTTP_200_OK)


RefreshView = TokenRefreshView  # alias برای خوانایی urls
