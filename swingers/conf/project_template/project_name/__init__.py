from __future__ import unicode_literals

import datetime
import os
import subprocess

VERSION = (0, 9, 0, 'alpha', 1)


def get_version(version=None):
    if version is None:
        version = VERSION

    assert len(version) == 5
    assert version[3] in ('alpha', 'beta', 'rc', 'final')

    # Now build the two parts of the version number:
    # main = X.Y[.Z]
    # sub = .devN - for pre-alpha releases
    #  | {a|b|c}N - for alpha, beta and rc releases

    parts = 2 if version[2] == 0 else 3
    main = '.'.join('{0}'.format(x) for x in version[:parts])

    sub = ''
    if version[3] == 'alpha' and version[4] == 0:
        hg_revision = get_mercurial_changeset()
        if hg_revision:
            sub = '.dev%s' % hg_revision

    elif version[3] != 'final':
        mapping = {'alpha': 'a', 'beta': 'b', 'rc': 'c'}
        sub = '{0}{1}'.format(mapping[version[3]], version[4])

    # see http://bugs.python.org/issue11638 - .encode('ascii')
    return '{0}{1}'.format(main, sub)


def get_mercurial_changeset():
    """
    Returns a numeric identifier of the latest mercurial changeset.

    The result is the UTC timestamp of the changeset in YYYYMMDDHHMMSS format.
    This value isn't guaranteed to be unique, but collisions are very unlikely,
    so it's sufficient for generating the development version numbers.
    """
    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hg_log = subprocess.Popen('hg tip --template "{date|hgdate}"',
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              shell=True, cwd=repo_dir,
                              universal_newlines=True)
    timestamp = hg_log.communicate()[0].split()[0]
    try:
        timestamp = datetime.datetime.utcfromtimestamp(int(timestamp))
    except ValueError:
        return None
    return timestamp.strftime('%Y%m%d%H%M%S')
