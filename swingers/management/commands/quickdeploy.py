from django.core.management.base import NoArgsCommand
from django.core.management import call_command
from django.contrib.staticfiles import storage
from django.conf import settings

from fabric.api import local

import os


class Command(NoArgsCommand):
    help = ("Runs `collectstatic --no-input -l` and fixes ownership and "
            "permissions for media/, cronjobs, . and STATIC_ROOT.")
    option_list = NoArgsCommand.option_list + tuple()

    def handle_noargs(self, *args, **options):
        # symlink for local storage or copy to remote destination
        try:
            storage.staticfiles_storage.path('')
        except NotImplementedError:
            link = False
        else:
            link = True

        output = ""
        call_command("collectstatic", link=link, interactive=False, **options)
        output += local("sudo chmod -R a=rX {0}".format(settings.STATIC_ROOT),
                        capture=True)
        if os.path.exists(settings.MEDIA_ROOT):
            output += local("sudo chown -RL :www-data {0}".format(
                settings.MEDIA_ROOT), capture=True)
            output += local("sudo chmod -R g=rwX {0}".format(
                settings.MEDIA_ROOT), capture=True)

        self.stderr.write(output)
