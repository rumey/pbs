from django.core.management.base import NoArgsCommand

from fabric.api import local


class Command(NoArgsCommand):
    help = "Runs pep8, cloccount and pyflakes."
    option_list = NoArgsCommand.option_list + tuple()

    def handle_noargs(self, **options):
        output = ""
        output += local('pep8 --exclude=virtualenv,migrations . > pep8.report',
                        capture=True)
        output += local('sloccount....', capture=True)
        output += local('pyflakes ', capture=True)
        self.stderr.write(output)
