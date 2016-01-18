from __future__ import (division, print_function, unicode_literals,
                        absolute_import)
from django.middleware.transaction import TransactionMiddleware
from django.db import transaction

import warnings
import django


ERROR_RESPONSES = [400, 401, 403, 404, 405, 409, 410, 500, 501]


class ResponseStatusTransactionMiddleware(TransactionMiddleware):
    """
    Transaction middleware. Differs slightly from the default Django
    transaction middleware in that it rolls back the transaction if a HTTP
    error response is generated. Note that if Http404, or any other exception
    is raised, this calls Django's TransactionMiddleware.process_exception,
    not this class' process_response.
    """
    def __init__(self, *args, **kwargs):
        warnings.warn("This is going to be deprecated, Django's "
                      "TransactionMiddleware superseedes this in Django 1.6",
                      PendingDeprecationWarning)

    def process_response(self, request, response):
        """Commits and leaves transaction management.

        Does nothing for django>=1.6."""
        if django.VERSION < (1, 6, 0):
            if transaction.is_managed():
                if transaction.is_dirty():
                    if response.status_code in ERROR_RESPONSES:
                        transaction.rollback()
                    else:
                        transaction.commit()
                transaction.leave_transaction_management()
        return response
