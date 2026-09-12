import os
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.accounts.models import User

class Command(BaseCommand):
    help = 'Delete all application/demo records and retain only the admin user and RBAC tables.'

    def add_arguments(self, parser):
        parser.add_argument('--password', default=os.environ.get('ADMIN_PASSWORD', ''))

    @transaction.atomic
    def handle(self, *args, **options):
        from django.apps import apps
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={'full_name': 'مدیر سیستم', 'is_active': True, 'is_staff': True, 'is_superuser': True},
        )
        password = options['password']
        if password:
            admin.set_password(password)
        admin.is_active = True
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()
        for model in apps.get_models():
            if model is User or model._meta.app_label in {'accounts', 'contenttypes', 'auth', 'admin', 'sessions', 'token_blacklist', 'auditlog'}:
                continue
            if not model._meta.can_migrate(None) or model._meta.proxy or model._meta.auto_created:
                continue
            model.objects.all().delete()
        User.objects.exclude(pk=admin.pk).delete()
        self.stdout.write(self.style.SUCCESS('Demo data reset: only admin user and RBAC/system tables remain.'))
        if password:
            self.stdout.write('admin password updated from ADMIN_PASSWORD/--password.')
