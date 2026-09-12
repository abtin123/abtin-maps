from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import OTPCode, Permission, Role, User


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ('code', 'label', 'module')


class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)

    class Meta:
        model = Role
        fields = ('code', 'label', 'scope', 'is_mobile', 'permissions')


class UserSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'full_name', 'mobile', 'email', 'role', 'permissions', 'last_login')

    def get_permissions(self, obj):
        return obj.all_permissions


def _token_pair(user):
    refresh = RefreshToken.for_user(user)
    if user.role_id:
        refresh['role'] = user.role.code
    refresh['full_name'] = user.full_name
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


class LoginSerializer(serializers.Serializer):
    """ورود با نام کاربری + رمز عبور"""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        request = self.context.get('request')
        user = authenticate(request, username=attrs['username'], password=attrs['password'])
        if not user:
            raise serializers.ValidationError('نام کاربری یا رمز عبور اشتباه است')
        if not user.is_active:
            raise serializers.ValidationError('حساب کاربری غیرفعال است')
        if request:
            user.last_login_ip = request.META.get('REMOTE_ADDR')
            user.last_login = timezone.now()
            user.save(update_fields=['last_login_ip', 'last_login'])
        attrs['user'] = user
        return attrs

    def create(self, validated_data):
        user = validated_data['user']
        return {'user': UserSerializer(user).data, 'tokens': _token_pair(user)}


class OTPRequestSerializer(serializers.Serializer):
    """درخواست OTP موبایل (بازاریاب / مامور پخش / مشتری)"""
    mobile = serializers.RegexField(r'^09\d{9}$', max_length=11, error_messages={
        'invalid': 'شماره موبایل باید با 09 شروع شود و ۱۱ رقم باشد'
    })

    def validate_mobile(self, mobile):
        if not User.objects.filter(mobile=mobile, is_active=True).exists():
            raise serializers.ValidationError('کاربری با این شماره موبایل یافت نشد')
        return mobile

    def create(self, validated_data):
        request = self.context.get('request')
        ip = request.META.get('REMOTE_ADDR') if request else None
        return OTPCode.issue(mobile=validated_data['mobile'], ip=ip)


class OTPVerifySerializer(serializers.Serializer):
    """تأیید OTP و صدور JWT"""
    mobile = serializers.RegexField(r'^09\d{9}$', max_length=11)
    code = serializers.CharField(min_length=6, max_length=6)

    def validate(self, attrs):
        otp = (
            OTPCode.objects
            .filter(mobile=attrs['mobile'], purpose=OTPCode.PURPOSE_LOGIN, consumed_at__isnull=True)
            .order_by('-created_at')
            .first()
        )
        if not otp or not otp.is_valid:
            raise serializers.ValidationError('کد منقضی شده یا معتبر نیست — دوباره درخواست دهید')
        if otp.code != attrs['code']:
            otp.attempts += 1
            otp.save(update_fields=['attempts'])
            raise serializers.ValidationError('کد وارد شده اشتباه است')
        otp.consume()
        try:
            user = User.objects.get(mobile=attrs['mobile'], is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError('کاربری با این شماره موبایل یافت نشد')
        attrs['user'] = user
        return attrs

    def create(self, validated_data):
        user = validated_data['user']
        return {'user': UserSerializer(user).data, 'tokens': _token_pair(user)}


class SwitchRoleSerializer(serializers.Serializer):
    """سوییچ نقش — فقط برای سوپرادمین یا کاربرانی که مجوز اختصاصی دارند"""
    role = serializers.SlugRelatedField(slug_field='code', queryset=Role.objects.all())

    def create(self, validated_data):
        user = self.context['request'].user
        user.role = validated_data['role']
        user.save(update_fields=['role'])
        return {'user': UserSerializer(user).data, 'tokens': _token_pair(user)}
