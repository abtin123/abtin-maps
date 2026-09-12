from pathlib import Path
from django.core.management import BaseCommand, call_command
from django.conf import settings

class Command(BaseCommand):
    help = 'Export all application data to a JSON backup file'
    def add_arguments(self, parser):
        parser.add_argument('--output', default='backup.json')
    def handle(self, *args, **options):
        output = Path(options['output']).resolve()
        with output.open('w', encoding='utf-8') as stream:
            call_command('dumpdata', exclude=['contenttypes', 'auth.permission', 'sessions'], indent=2, stdout=stream)
        self.stdout.write(self.style.SUCCESS(f'Backup created: {output}'))
