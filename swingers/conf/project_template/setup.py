#!/usr/bin/env python
"""
{{ project_name }}
==================

TODO: description

:copyright: (c) 2013 Department of Parks & Wildlife, see AUTHORS
            for more details.
:license: BSD 3-Clause, see LICENSE for more details.
"""
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand

import os

# Hack to prevent stupid "TypeError: 'NoneType' object is not callable" error
# in multiprocessing/util.py _exit_function when running `python
# setup.py test` (see
# http://www.eby-sarna.com/pipermail/peak/2010-May/003357.html)
for m in ('multiprocessing', 'billiard'):
    try:
        __import__(m)
    except ImportError:
        pass


class test(TestCommand):
    user_options = TestCommand.user_options + [
        ('with-xunit', None, "Enable xunit"),
        ('xunit-file=', None, "Xunit file"),
    ]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.with_xunit = False
        self.xunit_file = ''


tests_require = [
]

install_requires = [
]

version = __import__('{{ project_name }}').get_version()

setup(
    name='{{ project_name }}',
    version=version,
    author='<TODO>',
    author_email=('<TODO>'),
    url='https://bitbucket.org/dpaw/{{ project_name }}',
    description=('<TODO>'),
    packages=find_packages(exclude=['docs']),
    zip_safe=False,
    install_requires=install_requires,
    tests_require=tests_require,
    test_suite='{{ project_name }}.tests.runtests.runtests',
    scripts=[],
    cmdclass={'test': test},
    license='BSD License',
    include_package_data=True,
    keywords="<TODO> <TODO> dpaw",
    classifiers=[
        'Framework :: Django',
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
    ],
)
