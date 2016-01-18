from django.core.management.base import NoArgsCommand
from django.core.management import call_command


class Command(NoArgsCommand):
    help = "Runs `syncdbmigrate` and `quickinstall`."
    option_list = NoArgsCommand.option_list + tuple()
    requires_model_validation = False

    def handle_noargs(self, *args, **options):
        call_command("syncdbmigrate", **options)
        call_command("quickdeploy", **options)
