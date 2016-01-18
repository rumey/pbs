from __future__ import (division, print_function, unicode_literals,
                        absolute_import)

from django import forms

from swingers.forms.helpers import BaseFormHelper


class BaseAuditForm(forms.ModelForm):
    """
    A basic ModelForm meant to be used by any model type that inherits from
    Audit and/or ActiveModelMixin. It uses the BaseFormHelper and excludes the
    audit fields from the rendered form.
    Note that you can use this as the basis for other model types - the Meta
    class exclude will fail silently if a named field does not exist on that
    model.
    """
    def __init__(self, *args, **kwargs):
        self.helper = BaseFormHelper()
        super(BaseAuditForm, self).__init__(*args, **kwargs)

    class Meta:
        model = None
        # Exclude fields from the Audit and ActiveModelMixin abstract models.
        exclude = ['created', 'modified', 'creator', 'modifier',
                   'effective_from', 'effective_to']
