from django.utils import timezone
from rest_framework import serializers
from .models import Employee, Attendance, LeaveRequest


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = '__all__'


class AttendanceSerializer(serializers.ModelSerializer):
    worked_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = '__all__'

    def get_worked_minutes(self, obj):
        if not obj.check_in_at or not obj.check_out_at:
            return 0
        return max(0, int((obj.check_out_at - obj.check_in_at).total_seconds() // 60))

    def validate(self, attrs):
        check_in = attrs.get('check_in_at', getattr(self.instance, 'check_in_at', None))
        check_out = attrs.get('check_out_at', getattr(self.instance, 'check_out_at', None))
        if check_in and check_out and check_out < check_in:
            raise serializers.ValidationError('زمان خروج نمی‌تواند قبل از ورود باشد.')
        return attrs


class LeaveRequestSerializer(serializers.ModelSerializer):
    duration_days = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRequest
        fields = '__all__'
        read_only_fields = ('decided_by', 'decided_at', 'status')

    def get_duration_days(self, obj):
        return (obj.end_date - obj.start_date).days + 1

    def validate(self, attrs):
        if attrs.get('end_date') and attrs.get('start_date') and attrs['end_date'] < attrs['start_date']:
            raise serializers.ValidationError('تاریخ پایان مرخصی نمی‌تواند قبل از شروع باشد.')
        return attrs
