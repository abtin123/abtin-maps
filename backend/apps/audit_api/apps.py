from django.apps import AppConfig

class AuditApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.audit_api'

    def ready(self):
        from auditlog.registry import auditlog
        from django.apps import apps
        for label, names in {
            'sales': ['Invoice', 'Payment'],
            'inventory': ['InventoryReservation', 'StockDocument'],
            'delivery': ['DeliveryStop', 'Visit'],
            'finance': ['JournalEntry', 'Receipt', 'Cheque', 'FinancialDocument'],
            'hr': ['Attendance', 'LeaveRequest'],
        }.items():
            for name in names:
                try:
                    auditlog.register(apps.get_model(label, name))
                except (LookupError, TypeError):
                    pass
