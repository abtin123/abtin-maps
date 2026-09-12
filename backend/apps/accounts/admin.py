from django.contrib import admin

from .models import OTPCode, Permission, Role, RolePermission, User, UserPermission


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('code', 'label', 'module')
    list_filter = ('module',)
    search_fields = ('code', 'label')


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 0


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('code', 'label', 'is_mobile', 'is_system')
    inlines = [RolePermissionInline]


class UserPermissionInline(admin.TabularInline):
    model = UserPermission
    extra = 0


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'full_name', 'mobile', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active')
    search_fields = ('username', 'full_name', 'mobile')
    inlines = [UserPermissionInline]


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ('mobile', 'code', 'purpose', 'expires_at', 'consumed_at', 'attempts')
    list_filter = ('purpose',)
    search_fields = ('mobile',)
