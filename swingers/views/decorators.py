from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseRedirect

from functools import wraps

import logging


def cancel_view_m(view):
    """Wraps a (admin)class-based view and handles 'cancel' on POST"""
    def _dec(self, request, *args, **kwargs):
        """If request.POST['_cancel'] or request.POST['cancel'], ignore
        the view (cancel the save/update) and redirect to success url.

        * requires self.get_success_url() or self.success_url
        """
        if (request.method == 'POST' and
                (request.POST.get('cancel', None) is not None or
                 request.POST.get('_cancel', None) is not None)):
            if hasattr(self, 'get_success_url'):
                return HttpResponseRedirect(self.get_success_url())
            elif hasattr(self, 'success_url'):
                return HttpResponseRedirect(self.success_url)
            else:
                raise ImproperlyConfigured(
                    "{0} does not provide success_url.".format(
                        type(self).__name__))
        else:
            return view(self, request, *args, **kwargs)

    return _dec


def _log_view(func_name, request, logger_name='view_stats'):
    logger = logging.getLogger(logger_name)
    # Dump the message + the name of this function to the log.
    if request.user.is_anonymous():
        logger.info('{{"username":"anonymous", "view":"{0}", '
                    '"path":"{1}"}}'.format(func_name, request.path))
    else:
        logger.info('{{"username":"{0}", "view":"{1}", "path":"{2}"}}'
                    .format(request.user.username, func_name,
                            request.path))


def log_view_dec(logger_name='view_stats'):
    """Decorator to log the current view and user."""
    def dec(func):
        @wraps(func)
        def inner(request, *args, **kwargs):
            _log_view(func.__name__, request, logger_name=logger_name)
            return func(request, *args, **kwargs)
        return inner
    return dec


def log_view_dec_m(logger_name='view_stats'):
    """Method decorator to log the current view and user."""
    def dec(view):
        @wraps(view)
        def inner(self, request, *args, **kwargs):
            _log_view("{0}.{1}".format(self.__class__.__name__, view.__name__),
                      request, logger_name=logger_name)
            return view(self, request, *args, **kwargs)
        return inner
    return dec
