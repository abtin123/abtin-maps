from rest_framework import serializers
from .models import Account, JournalEntry, JournalLine, Receipt, Cheque, FinancialDocument, Payroll, Commission, SalesTarget


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = '__all__'


class JournalLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalLine
        fields = '__all__'
        read_only_fields = ('entry',)

    def validate(self, attrs):
        debit, credit = attrs.get('debit', 0), attrs.get('credit', 0)
        if bool(debit) == bool(credit):
            raise serializers.ValidationError('هر خط باید دقیقاً یکی از بدهکار یا بستانکار را داشته باشد.')
        return attrs


class JournalEntrySerializer(serializers.ModelSerializer):
    lines = JournalLineSerializer(many=True, read_only=True)
    total_debit = serializers.SerializerMethodField()
    total_credit = serializers.SerializerMethodField()

    class Meta:
        model = JournalEntry
        fields = '__all__'
        read_only_fields = ('created_by', 'posted_at', 'status')

    def get_total_debit(self, obj):
        return sum((line.debit for line in obj.lines.all()), 0)

    def get_total_credit(self, obj):
        return sum((line.credit for line in obj.lines.all()), 0)


class ReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Receipt
        fields = '__all__'
        read_only_fields = ('received_by',)


class ChequeSerializer(serializers.ModelSerializer):
    is_due_soon = serializers.SerializerMethodField()
    class Meta:
        model = Cheque
        fields = '__all__'

    def get_is_due_soon(self, obj):
        from django.utils import timezone
        return obj.due_date <= timezone.localdate() + timezone.timedelta(days=7) and obj.status in (Cheque.REGISTERED, Cheque.DEPOSITED)


class FinancialDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialDocument
        fields = '__all__'
        read_only_fields = ('created_by', 'journal_entry', 'is_void')


class PayrollSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payroll
        fields = '__all__'
        read_only_fields = ('created_by', 'net_amount')


class CommissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commission
        fields = '__all__'
        read_only_fields = ('created_by', 'amount')


class SalesTargetSerializer(serializers.ModelSerializer):
    achievement_percent = serializers.ReadOnlyField()
    class Meta:
        model = SalesTarget
        fields = '__all__'
        read_only_fields = ('created_by', 'achievement_percent')


class JournalPostSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default='')
