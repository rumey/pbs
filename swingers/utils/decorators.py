from functools import wraps

import os
import tempfile
import shutil


def workdir(remove=True):
    """
    Wraps a function and handles directory creation/removal where needed.

    If no directory is specified as the first argument to the decorated
    function, workdir will create a temporary directory to work in.

    If remove=False, workdir won't delete the directory that has been created.

    Usage:
        @workdir()
        def decorated_function(*args, **kwargs):
            # do file creation/deletion in the current directory.

        # do work in a temporary directory, deleting the directory after
        # returning from the function.
        decorated_function()

        # do work in a specified directory, deleting the directory after
        # returning from the function.
        decorated_function('/some/path')

        @workdir(remove=False)
        def decorated_function(*args, **kwargs):
            # do file creation/deletion in the current directory.
            # will not get removed after being called

        # do work in a temporary directory, leaving the contents intact after
        # returning from the function.
        decorated_function()

        # do work in a specified directory, keeping the contents intact after
        # returning from the function.
        decorated_function('/some/path')
    """
    def decorator(func):
        @wraps(func)
        def inner(directory=None, *args, **kwargs):
            cwd = os.getcwd()
            if directory is not None and isinstance(directory, basestring):
                directory = os.path.abspath(directory)
                if not os.path.exists(directory):
                    os.makedirs(directory)
            elif directory is not None:
                args = tuple([directory] + list(args))
                directory = tempfile.mkdtemp()
            else:
                directory = tempfile.mkdtemp()

            os.chdir(directory)
            try:
                result = func(*args, **kwargs)
            finally:
                os.chdir(cwd)
                if remove:
                    shutil.rmtree(directory)
            return result
        return inner
    return decorator
