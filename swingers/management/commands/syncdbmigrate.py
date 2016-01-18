from django.core.management.base import NoArgsCommand
from django.core.management import call_command


class Command(NoArgsCommand):
    help = ("Runs `syncdb --no-input`, `update_permissions`, "
            "`migrate --no-initial-data` and `migrate`.")
    option_list = NoArgsCommand.option_list + tuple()
    requires_model_validation = False

    def handle_noargs(self, *args, **options):
        call_command("syncdb", interactive=False, **options)
        call_command("update_permissions", **options)
        call_command("migrate", no_initial_data=True, **options)
        call_command("migrate", **options)
