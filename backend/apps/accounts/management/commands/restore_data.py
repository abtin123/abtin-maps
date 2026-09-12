from pathlib import Path
from django.core.management import BaseCommand, call_command

class Command(BaseCommand):
    help = 'Restore application data from a JSON backup file'
    def add_arguments(self, parser):
        parser.add_argument('input')
    def handle(self, *args, **options):
        source = Path(options['input']).resolve()
        if not source.is_file():
            raise self.CommandError(f'Backup not found: {source}')
        call_command('loaddata', str(source))
        self.stdout.write(self.style.SUCCESS(f'Backup restored: {source}'))
