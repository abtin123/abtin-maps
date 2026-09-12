from rest_framework.permissions import BasePermission


class HasPermissionCode(BasePermission):
    """گارد Permission-Based روی ویوها:
    class MyView(APIView):
        permission_classes = [HasPermissionCode('invoices.confirm')]
    یا روی ویو: required_permission = 'invoices.confirm'
    """
    required_permission = None

    def __init__(self, code=None):
        if code:
            self.required_permission = code

    def has_permission(self, request, view):
        code = self.required_permission or getattr(view, 'required_permission', None)
        if not code:
            return request.user and request.user.is_authenticated
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.has_perm_code(code)
        )


class IsSuperAdmin(BasePermission):
    """فقط نقش مدیر کل / سوپریوزر جنگو"""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or (user.role_id and user.role.code == 'super_admin'))
        )
