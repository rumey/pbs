#!/usr/bin/env python
from django.core.management import ManagementUtility

from os import path

import swingers


class SwingersManagementUtility(ManagementUtility):
    """We add our own tasks and stuff, this could probably replace our
    fabfile.
    TODO:
    """
    def __init__(self, argv=None):
        super(SwingersManagementUtility, self).__init__(argv)
        if ((len(self.argv) > 1 and self.argv[1].lower() == 'startproject' and
             not any(map(lambda x: x.startswith('--template'), self.argv)))):
            # if we got a startproject command without template, give it our
            # template
            swingers_dir = swingers.__path__[0]
            template_dir = path.join(swingers_dir, "conf", "project_template")
            self.argv.append('--template={0}'.format(template_dir))
            self.argv.append('-e py,txt,in,rst')   # just to make sure :)


def execute_from_command_line(argv=None):
    utility = SwingersManagementUtility(argv)
    utility.execute()


if __name__ == "__main__":
    execute_from_command_line()
