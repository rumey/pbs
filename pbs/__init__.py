
import errno
import os
import threading
import time
from hashlib import sha1

from django.conf import settings
import logging

class SemaphoreException(Exception):
    """An exception that get thrown when an error occurs in the mutex semphore context"""

class mutex(object):
    """A semaphore Context Manager that uses a temporary file for locking.
    Only one thread or process can get a lock on the file at once.
    it can be used to mark a block of code as being executed exclusively
    by some thread. see `mutex <http://en.wikipedia.org/wiki/Mutual_exclusion>`_.
    usage::
    from __future__ import with_statement
    from pbs import mutex
    with mutex:
    print "hi only one thread will be executing this block of code at a time."
    Mutex raises an :class:`easymode.utils.SemaphoreException` when it has to wait to
    long to obtain a lock or when it can not determine how long it was waiting.
    :param max_wait: The maximum amount of seconds the process should wait to obtain\
    the semaphore.
    :param lockfile: The path and name of the pid file used to create the semaphore.
    """

    def __init__(self, lockname,max_wait=None, burn_id=None, user=None):
        # the maximum reasonable time for aprocesstobe
        self.burn_id = burn_id
        self.user = user
        if max_wait is not None:
            self.max_wait = max_wait
        else:
            self.max_wait = 10
        self.logger = logging.getLogger('pbs')
        self.lockname = lockname

        self.we_got_lock = False

        self.lockfile = os.path.join( "/tmp/", sha1(settings.SECRET_KEY).hexdigest() + '.'+lockname+ '.semaphore')

    def __enter__(self):
        while True:
            try:
                # if the file exists you can not create it and get an exclusive lock on it
                # this is an atomic operation.
                file_descriptor = os.open(self.lockfile, os.O_EXCL | os.O_RDWR | os.O_CREAT)
                # we created the lockfile, so we're the owner
                self.logger.info('Created lock: '+self.lockname + ' lock file: ' + self.lockfile)
                break
            except OSError as e:
                if e.errno != errno.EEXIST:
                    # should not occur
                    raise e

            # if we got here the file exists so lets see
            # how long we are waiting for it
            try:
                # the lock file exists, try to stat it to get its age
                # and read it's contents to report the owner PID
                file_contents = open(self.lockfile, "r")
                file_last_modified = os.path.getmtime(self.lockfile)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise SemaphoreException("%s exists but stat() failed: %s" %
                        (self.lockfile, e.strerror)
                    )
                # we didn't create the lockfile, so it did exist, but it's
                # gone now. Just try again
                continue
            self.logger.info('Lock already exists.')
            # we didn't create the lockfile and it's still there, check
            # its age
            mtime = time.time() - file_last_modified
            if mtime > settings.MAX_LOCK_TIME: # 60*4
                pid = file_contents.readline()
                user = file_contents.readline()
                os.remove(self.lockfile)
                raise SemaphoreException('{} has been locked for more than {} minutes by User {} (PID {}). Removing Lock.<br/><br/>Please Retry.'.format(
                    self.burn_id, int(settings.MAX_LOCK_TIME/60), user, pid))

            if mtime > self.max_wait:
                pid = file_contents.readline()
                user = file_contents.readline()
                raise SemaphoreException('{0} has been locked for more than {1:.2f} minutes by User {2} (PID {3}).<br/><br/>' \
                    'Retry in {4:.2f} minutes'.format(
                    self.burn_id, mtime/60.0, user, pid, (settings.MAX_LOCK_TIME-mtime)/60.0))

            # it's not been locked too long, wait a while and retry
            file_contents.close()
            time.sleep(1)

        # if we get here. we have the lockfile. Convert the os.open file
        # descriptor into a Python file object and record our PID in it
        self.logger.debug('We have the lock')
        self.we_got_lock = True
        file_handle = os.fdopen(file_descriptor, "w")
        file_handle.write('{}\n{}'.format(os.getpid(), self.user.get_full_name()))
        file_handle.close()

    def __exit__(self, exc_type, exc_value, traceback):
        #Remove the lockfile, releasing the semaphore for other processes to obtain
        if self.we_got_lock:
            os.remove(self.lockfile)
            if os.path.isfile(self.lockfile):
                # stil exists - retry ...
                self.logger.info('Lock still exists. Retrying to release ... ' + self.lockname)
                time.sleep(5)
                os.remove(self.lockfile)

            if os.path.isfile(self.lockfile):
                self.logger.info('Failed to Released lock ' + self.lockname)
            else:
                self.logger.info('Released lock ' + self.lockname)
        else:
            self.logger.info("Not our lock to release")
