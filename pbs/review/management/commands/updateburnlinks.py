from django.core.management.base import BaseCommand, CommandError
from pbs.review.models import BurnProgramLink

class Command(BaseCommand):
    help = 'Updates the links between ePFP data and the spatial geodatabase.'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        try:
            BurnProgramLink.populate()
        except Exception as e:
            raise CommandError(e)

        self.stdout.write('Burn Program successfully linked.')

