from django.contrib import admin
from django.db.models import Q

import re
import gc


def queryset_iterator(queryset, chunksize=1000):
    """
    Iterate over a queryset ordered by the primary key.

    This method loads a maximum of chunksize (default: 1000) rows in its
    memory at the same time while django normally would load all rows in
    it's memory. Using the iterator() method only causes it to not preload
    all the classes.

    Note that the implementation of the iterator does not support ordered
    querysets.
    """
    pk = 0
    last_pk = queryset.order_by('-pk')[0].pk
    queryset = queryset.order_by('pk')
    while pk < last_pk:
        for row in queryset.filter(pk__gt=pk)[:chunksize]:
            pk = row.pk
            yield row
        gc.collect()


FIND_TERMS_RE = re.compile(r'"([^"]+)"|(\S+)')
NORMALISE_RE = re.compile(r'\s{2,}')


def normalise_query(query_string, find_terms=None, normalise_spaces=None):
    """
    Splits the query string in invidual keywords, getting rid of unecessary
    spaces and grouping quoted words together.

    Example:

    >>> normalise_query('  some random  words "with   quotes  " and   spaces')
    >>> ['some', 'random', 'words', 'with quotes ', 'and', 'spaces']
    """
    if find_terms is None:
        find_terms = FIND_TERMS_RE.finditer
    if normalise_spaces is None:
        normalise_spaces = NORMALISE_RE.sub

    return [normalise_spaces(' ',
                             (t.group(0) or t.group(1))
                             .strip().strip('"').strip("'"))
            for t in find_terms(query_string)]


def get_query(query_string, search_fields):
    """
    Returns a query which is a combination of Q objects. That combination
    aims to search keywords within a model by testing the given search fields.
    """
    # Query to search for every search term
    query = None
    terms = normalise_query(query_string)
    for term in terms:
        # Query to search for a given term in each field
        or_query = None
        for field_name in search_fields:
            q = Q(**{"%s__icontains" % field_name: term})
            print {"%s__icontains" % field_name: term}
            if or_query is None:
                or_query = q
            else:
                or_query = or_query | q
        if query is None:
            query = or_query
        else:
            query = query & or_query
    return query


def filter_queryset(search_string, model, queryset):
    """
    Function to dynamically filter a model queryset, based upon the
    search_fields defined in admin.py for that model. If search_fields is not
    defined, the queryset is returned unchanged.
    """
    # Replace single-quotes with double-quotes
    search_string = search_string.replace("'", r'"')
    if admin.site._registry[model].search_fields:
        search_fields = admin.site._registry[model].search_fields
        entry_query = get_query(search_string, search_fields)
        queryset = queryset.filter(entry_query)
    return queryset
