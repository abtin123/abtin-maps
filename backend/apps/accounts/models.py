"""
Accounts domain — مدل کاربر سفارشی + RBAC (Role/Permission) + OTP موبایل
بر اساس ERD: users n—1 roles ، roles n—n permissions (role_permissions) ،
users n—n permissions (user_permissions)
"""
import random
from datetime import timedelta

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone


class Permission(models.Model):
    """مجوزهای سیستم — permission_based navigation و گارد API"""
    code = models.CharField(max_length=64, unique=True, db_index=True)  # e.g. invoices.confirm
    label = models.CharField(max_length=128)  # برچسب فارسی
    module = models.CharField(max_length=32, db_index=True)  # sales / inventory / finance / ...
    description = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['module', 'code']

    def __str__(self):
        return f'{self.module}:{self.code}'


class Role(models.Model):
    """۱۴ نقش سیستم — متناظر ROLES در فرانت‌اند"""
    code = models.SlugField(max_length=32, unique=True, db_index=True)  # super_admin ...
    label = models.CharField(max_length=64)  # مدیر کل ...
    scope = models.CharField(max_length=255, blank=True, default='')
    is_mobile = models.BooleanField(default=False)
    is_system = models.BooleanField(default=False)  # نقش‌های سیستمی قابل حذف نیستند
    permissions = models.ManyToManyField(
        Permission, through='RolePermission', related_name='roles', blank=True
    )

    class Meta:
        ordering = ['code']

    def __str__(self):
        return self.label


class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('role', 'permission')


class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('نام کاربری الزامی است')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """مدل کاربر سفارشی — لاگین با username یا موبایل (OTP)"""
    username = models.CharField(max_length=64, unique=True, db_index=True)
    mobile = models.CharField(max_length=11, unique=True, null=True, blank=True, db_index=True)
    full_name = models.CharField(max_length=128, blank=True, default='')
    email = models.EmailField(blank=True, default='')

    role = models.ForeignKey(
        Role, on_delete=models.PROTECT, related_name='users', null=True, blank=True
    )
    extra_permissions = models.ManyToManyField(
        Permission,
        through='UserPermission',
        related_name='users_with_extra',
        blank=True,
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ['username']

    def __str__(self):
        return f'{self.username} ({self.role_id or "بدون نقش"})'

    @property
    def all_permissions(self):
        """مجموع مجوزهای نقش + مجوزهای اختصاصی کاربر"""
        codes = set()
        if self.role_id:
            codes |= set(self.role.permissions.values_list('code', flat=True))
        codes |= set(self.extra_permissions.values_list('code', flat=True))
        return sorted(codes)

    def has_perm_code(self, code):
        return self.is_superuser or code in self.all_permissions


class UserPermission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='extra_user_permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'permission')


class OTPCode(models.Model):
    """کد یک‌بارمصرف موبایل — برای بازاریاب / مامور پخش / مشتری"""
    PURPOSE_LOGIN = 'login'
    PURPOSE_RESET = 'reset_password'
    PURPOSES = [(PURPOSE_LOGIN, 'ورود'), (PURPOSE_RESET, 'بازیابی رمز')]

    mobile = models.CharField(max_length=11, db_index=True)
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=PURPOSES, default=PURPOSE_LOGIN)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    request_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['mobile', 'purpose', 'consumed_at'])]

    OTP_TTL_MINUTES = 2
    MAX_ATTEMPTS = 5

    @classmethod
    def issue(cls, mobile, purpose=PURPOSE_LOGIN, ip=None):
        # ابطال کدهای فعال قبلی
        cls.objects.filter(mobile=mobile, purpose=purpose, consumed_at__isnull=True).update(
            consumed_at=timezone.now()
        )
        code = f'{random.SystemRandom().randint(0, 999999):06d}'
        return cls.objects.create(
            mobile=mobile,
            code=code,
            purpose=purpose,
            expires_at=timezone.now() + timedelta(minutes=cls.OTP_TTL_MINUTES),
            request_ip=ip,
        )

    @property
    def is_valid(self):
        return (
            self.consumed_at is None
            and self.attempts < self.MAX_ATTEMPTS
            and self.expires_at > timezone.now()
        )

    def consume(self):
        self.consumed_at = timezone.now()
        self.save(update_fields=['consumed_at'])
