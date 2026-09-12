from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.accounts.permissions import HasPermissionCode
from .models import Employee, Attendance, LeaveRequest
from .serializers import EmployeeSerializer, AttendanceSerializer, LeaveRequestSerializer


class HRViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasPermissionCode]
    permission_map = {'list': 'hr.view', 'retrieve': 'hr.view', 'create': 'hr.view', 'update': 'hr.view', 'partial_update': 'hr.view', 'destroy': 'hr.view'}
    def get_permissions(self):
        self.required_permission = self.permission_map.get(self.action, 'hr.view')
        return super().get_permissions()


class EmployeeViewSet(HRViewSet):
    queryset = Employee.objects.select_related('user', 'branch')
    serializer_class = EmployeeSerializer
    permission_map = {**HRViewSet.permission_map, 'create': 'hr.leave_manage', 'update': 'hr.leave_manage', 'partial_update': 'hr.leave_manage', 'destroy': 'hr.leave_manage'}


class AttendanceViewSet(HRViewSet):
    queryset = Attendance.objects.select_related('employee')
    serializer_class = AttendanceSerializer
    permission_map = {**HRViewSet.permission_map, 'create': 'hr.attendance', 'update': 'hr.attendance', 'partial_update': 'hr.attendance', 'check_in': 'hr.attendance', 'check_out': 'hr.attendance'}

    def _get_or_create_today(self, employee_id):
        attendance, _ = Attendance.objects.get_or_create(employee_id=employee_id, work_date=timezone.localdate())
        return attendance

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def check_in(self, request):
        employee_id = request.data.get('employee')
        if not employee_id:
            return Response({'detail': 'employee الزامی است.'}, status=400)
        attendance = self._get_or_create_today(employee_id)
        if attendance.check_in_at:
            return Response({'detail': 'ورود امروز قبلاً ثبت شده است.'}, status=400)
        attendance.check_in_at = timezone.now()
        attendance.check_in_latitude = request.data.get('latitude')
        attendance.check_in_longitude = request.data.get('longitude')
        attendance.save(update_fields=['check_in_at','check_in_latitude','check_in_longitude'])
        return Response(self.get_serializer(attendance).data)

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def check_out(self, request):
        employee_id = request.data.get('employee')
        if not employee_id:
            return Response({'detail': 'employee الزامی است.'}, status=400)
        attendance = self._get_or_create_today(employee_id)
        if not attendance.check_in_at:
            return Response({'detail': 'ابتدا ورود را ثبت کنید.'}, status=400)
        if attendance.check_out_at:
            return Response({'detail': 'خروج امروز قبلاً ثبت شده است.'}, status=400)
        attendance.check_out_at = timezone.now()
        attendance.check_out_latitude = request.data.get('latitude')
        attendance.check_out_longitude = request.data.get('longitude')
        attendance.save(update_fields=['check_out_at','check_out_latitude','check_out_longitude'])
        return Response(self.get_serializer(attendance).data)


class LeaveRequestViewSet(HRViewSet):
    queryset = LeaveRequest.objects.select_related('employee', 'decided_by')
    serializer_class = LeaveRequestSerializer
    permission_map = {**HRViewSet.permission_map, 'create': 'hr.leave_manage', 'update': 'hr.leave_manage', 'partial_update': 'hr.leave_manage', 'decide': 'hr.leave_manage'}

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def decide(self, request, pk=None):
        leave = LeaveRequest.objects.select_for_update().get(pk=pk)
        if leave.status != LeaveRequest.PENDING:
            return Response({'detail': 'این درخواست قبلاً تعیین تکلیف شده است.'}, status=400)
        decision = request.data.get('status')
        if decision not in (LeaveRequest.APPROVED, LeaveRequest.REJECTED):
            return Response({'detail': 'status باید approved یا rejected باشد.'}, status=400)
        leave.status = decision; leave.decided_by = request.user; leave.decided_at = timezone.now(); leave.save(update_fields=['status', 'decided_by', 'decided_at'])
        return Response(self.get_serializer(leave).data)
