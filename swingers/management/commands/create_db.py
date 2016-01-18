from django.core.management.base import NoArgsCommand
from django.core.management import call_command
from django.conf import settings

from fabric.api import local, hide
from fabric.context_managers import settings as fabric_settings
from fabric.contrib.files import _escape_for_regex


class Command(NoArgsCommand):
    help = ("Creates and starts a local postgis-enabled postgresql db based on"
            " the `settings.DATABASES['default']`")
    option_list = NoArgsCommand.option_list + tuple()
    requires_model_validation = False

    def configure(self, filename, value):
        if len(value.split('=')) == 2:
            directive, _ = value.split('=')
        else:
            directive = value

        directive = _escape_for_regex(directive)
        value = _escape_for_regex(value)

        # can't use contrib.files.[contains, sed, append] because they need a
        # host to connect to (they run as `run` or `sudo`
        with fabric_settings(hide('everything'), warn_only=True):
            contains = local(
                "grep -q '^{0}' '{1}'".format(directive, filename),
                capture=True).succeeded

        if contains:
            local('sudo sed -i.bak -r -e "s/{0}/{1}/g" "{2}"'.format(
                '^{0}.*$'.format(directive), value, filename))
        else:
            local('sudo sed -i.bak -e "\$a {0}" "{1}"'.format(value, filename))

    def handle_noargs(self, *args, **options):
        #local("sudo -u postgres pg_dropcluster --stop 9.1 %(USER)s || true"
        #      % settings.DATABASES['default'])
        local("sudo -u postgres pg_createcluster -p %(PORT)s 9.1 %(USER)s "
              "--start" % settings.DATABASES['default'])
        local("echo PASS: %(PASSWORD)s" % settings.DATABASES['default'])
        local("sudo -u postgres createuser -s %(USER)s -p %(PORT)s -P"
              % settings.DATABASES['default'])

        self.configure("/etc/postgresql/9.1/%(USER)s/postgresql.conf"
                       % settings.DATABASES['default'],
                       "listen_addresses = '*'")
        self.configure("/etc/postgresql/9.1/%(USER)s/postgresql.conf"
                       % settings.DATABASES['default'], "wal_level = archive")
        self.configure("/etc/postgresql/9.1/%(USER)s/pg_hba.conf"
                       % settings.DATABASES['default'],
                       "host    all     all     10.0.0.0/8  md5")

        local("sudo pg_ctlcluster 9.1 %(USER)s restart"
              % settings.DATABASES['default'])
        local("sudo -u postgres psql -p %(PORT)s -c 'DROP DATABASE %(NAME)s;'"
              " || true" % settings.DATABASES['default'])
        local(
            "sudo -u postgres psql -p %(PORT)s -c 'CREATE DATABASE %(NAME)s;'"
            % settings.DATABASES['default'])
        local("sudo -u postgres psql -p %(PORT)s "
              "-c 'CREATE EXTENSION postgis;' %(NAME)s"
              % settings.DATABASES['default'])
