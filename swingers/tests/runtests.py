#!/usr/bin/env python

import os
import sys
import warnings

warnings.simplefilter('ignore')

from django.conf import settings

if not settings.configured:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'swingers.tests.settings'

# TODO: if we need to test on multiple databases.
#test_db = os.environ.get('DB', 'sqlite')
#if test_db == 'mysql':
#    settings.DATABASES['default'].update({
#    })
#elif test_db == 'postgres':
#    settings.DATABASES['default'].update({
#    })
#elif test_db == 'sqlite':
#    settings.DATABASES['default'].update({
#    })

RUNTESTS_DIR = os.path.abspath(os.path.dirname(__file__))
# put 'tests/../../' onto sys.path
DJANGO_SWINGERS_DIR = os.path.dirname(os.path.dirname(RUNTESTS_DIR))
if not DJANGO_SWINGERS_DIR in sys.path:
    sys.path.insert(0, DJANGO_SWINGERS_DIR)


def runtests(*test_args, **kwargs):
    from django_nose import NoseTestSuiteRunner
    if 'south' in settings.INSTALLED_APPS:
        from south.management.commands import patch_for_test_db_setup
        patch_for_test_db_setup()

    test_args = test_args or []

    if 'verbosity' in kwargs:
        kwargs['verbosity'] = int(kwargs['verbosity'])

    kwargs.setdefault('interactive', False)

    test_args.append('--with-coverage')
    test_args.append('--cover-package=swingers')
    test_args.append('--cover-xml')
    test_args.append('--cover-xml-file=coverage.xml')

    test_runner = NoseTestSuiteRunner(**kwargs)

    failures = test_runner.run_tests(test_args)
    sys.exit(failures)


if __name__ == '__main__':
    from optparse import OptionParser
    usage = "%prog [options] [module module module ...]"
    parser = OptionParser(usage=usage)
    parser.add_option(
        '-v', '--verbosity', action='store', dest='verbosity', default=1,
        type='choice', choices=['0', '1', '2', '3'],
        help='Verbosity level; 0=minimal output, 1=normal output, 2=all '
             'output')
    parser.add_option(
        '--noinput', action='store_false', dest='interactive', default=True,
        help='Tells Django to NOT prompt the user for input of any kind.')
    parser.add_option(
        '--failfast', action='store_true', dest='failfast', default=False,
        help='Tells Django to stop running the test suite after first failed '
             'test.')
    parser.add_option(
        '--settings',
        help='Python path to settings module, e.g. "myproject.settings". If '
             'this isn\'t provided, the DJANGO_SETTINGS_MODULE environment '
             'variable will be used.')
    parser.add_option(
        '--bisect', action='store', dest='bisect', default=None,
        help='Bisect the test suite to discover a test that causes a test '
             'failure when combined with the named test.')
    parser.add_option(
        '--pair', action='store', dest='pair', default=None,
        help='Run the test suite in pairs with the named test to find problem '
             'pairs.')
    parser.add_option(
        '--liveserver', action='store', dest='liveserver', default=None,
        help='Overrides the default address where the live server (used with '
             'LiveServerTestCase) is expected to run from. The default value '
             'is localhost:8081.'),
    options, args = parser.parse_args()
    if options.settings:
        os.environ['DJANGO_SETTINGS_MODULE'] = options.settings
    elif "DJANGO_SETTINGS_MODULE" not in os.environ:
        parser.error("DJANGO_SETTINGS_MODULE is not set in the environment. "
                     "Set it or use --settings.")
    else:
        options.settings = os.environ['DJANGO_SETTINGS_MODULE']

    if options.liveserver is not None:
        os.environ['DJANGO_LIVE_TEST_SERVER_ADDRESS'] = options.liveserver

    runtests(*args, **options.__dict__)
