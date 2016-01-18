from django.middleware.cache import (UpdateCacheMiddleware as
                                     DjangoUpdateCacheMiddleware)
from django.utils.cache import get_max_age, learn_cache_key
from django.db import connection

import re
import itertools
import logging


logger = logging.getLogger("log." + __name__)


class UpdateCacheMiddleware(DjangoUpdateCacheMiddleware):
    """This is a caching middleware built on top of django's caching
    middleware.

    - it builds up an associative array of cache_key(request) to read db tables
    - it examines django.db.connections to determine which db tables were
    written to and consequently deletes all cache_keys that read from those db
    tables
    - it uses django's caching middleware to determine the cache keys, fetch
    from cache, update cache, etc.
    - the added functionality is invalidating cache entries based on what db
    tables were written to.

    * still a bit freash and alpha :), needs some testing.
    """
    read_table_regex = re.compile(r'(?:FROM|JOIN) +"([^ ]+)" +')
    write_table_regex = re.compile(r'(?:INTO|FROM|UPDATE|JOIN) +"([^ ]+)" +')
    cache_table_key = ("swingers.middleware.UpdateCacheMiddleware.." +
                       "cache_keys_for_table_{0}")

    def _will_update_cache(self, request, response):
        if ((not self._should_update_cache(request, response) or
             getattr(response, 'streaming', False) or
             response.status_code != 200)):
            return False
        return bool(self._get_timeout(response))

    def _get_timeout(self, response):
        timeout = get_max_age(response)
        if timeout is None:
            timeout = self.cache_timeout
        return timeout

    def get_and_set_readtables(self, cache_key):
        read = (self.read_table_regex.finditer(q['sql'])
                for q in connection.queries
                if (q['sql'].startswith("SELECT") or
                    q['sql'].startswith('QUERY = u\'SELECT')))
        readtables = []
        for r in itertools.chain(*read):
            if r is not None:
                if r.group(1) not in readtables:
                    readtables.append(r.group(1))

        # TODO: can we run into race conditions here??? !!!
        for table in readtables:
            table_keys = self.cache.get(self.cache_table_key.format(table), [])
            if not cache_key in table_keys:
                table_keys.append(cache_key)
            self.cache.set(self.cache_table_key.format(table), table_keys,
                           60 * 60 * 24 * 14)
        return readtables

    def process_response(self, request, response):
        # determine which db tables (read/write) have been touched in this
        # request/response, update the read table -> *cache_keys mapping
        # accordingly,
        # also flush appropriate cache_keys for views that read from tables
        # that were written by this request

        # TODO: a simple way (GET request) to invalidate certain cached views
        # TODO: cache only if not settings.DEBUG (do we really want to cache
        # while developing???
        # TODO: can we speed this up???
        # TODO: default cache timeout
        # TODO: bulk delete, bulk set???
        # TODO: django.db.connection.queries doesn't work when
        # not settings.DEBUG!!! :( now the connnection is patched with a
        # connection_created signal, needs a better patch

        # if updating cache, also update the cache table -> *cache_keys mapping
        if self._will_update_cache(request, response):
            cache_key = learn_cache_key(request, response,
                                        self._get_timeout(response),
                                        self.key_prefix, cache=self.cache)
            if hasattr(response, 'render') and callable(response.render):
                response.add_post_render_callback(
                    lambda r: self.get_and_set_readtables(cache_key)
                )
            else:
                self.get_and_set_readtables(cache_key)

            logger.debug('Updating readtables for cache_key: {0}'
                         .format(cache_key))
        #

        # flush appropriate parts of the cache
        written = (self.write_table_regex.finditer(q['sql'])
                   for q in connection.queries
                   if not (q['sql'].startswith("SELECT") or
                           q['sql'].startswith('QUERY = u\'SELECT')))
        writtentables = []
        for w in itertools.chain(*written):
            if w is not None:
                if w.group(1) not in writtentables:
                    writtentables.append(w.group(1))

        # TODO: use iterators instead
        if len(writtentables):
            cache_keys_for_deletion = list(
                set(reduce(lambda x, y: x + y,
                           [self.cache.get(self.cache_table_key.format(w), [])
                            for w in writtentables])
                    )
            )
            logger.debug('Flushing cache keys \n{0}'
                         .format("\n".join(cache_keys_for_deletion)))
            map(self.cache.delete, cache_keys_for_deletion)
        #

        return super(UpdateCacheMiddleware, self).process_response(request,
                                                                   response)


from django.db.backends.signals import connection_created
from django.conf import settings


# monkey-patch the connection cursor so that db.connection.queries works even
# when `not settings.DEBUG`
# TODO: create a better method to log the queries (with lower overhead than the
# debug cursor)
def patch_db_cursor(sender, connection, **kwargs):
    if not settings.DEBUG:
        connection.use_debug_cursor = True

connection_created.connect(patch_db_cursor,
                           dispatch_uid="swingers-patch_cursor")
