from __future__ import (division, print_function, unicode_literals,
                        absolute_import)

from swingers.sauth.forms import BaseAuditForm

from .models import Duck


class DuckForm(BaseAuditForm):
    class Meta:
        model = Duck
