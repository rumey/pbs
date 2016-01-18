from django.core.management.base import NoArgsCommand
from django.db import connection
from django.core.management import call_command


class Command(NoArgsCommand):
    help = "Deletes all tables in the 'default' database."
    option_list = NoArgsCommand.option_list + tuple()

    def handle_noargs(self, **options):
        cursor = connection.cursor()
        tables = connection.introspection.django_table_names(
            only_existing=True)
        for table in tables:
            command = "DROP TABLE %s CASCADE;" % table
            cursor.execute(command)
            self.stderr.write("Executed ... %s" % command)
        cursor.execute("COMMIT;")
        self.stderr.write("Running syncdbmigrate ...")
        call_command("syncdbmigrate", **options)
