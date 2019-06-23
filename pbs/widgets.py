from django import forms

class NullBooleanSelect(forms.widgets.NullBooleanSelect):
    """
    A Select Widget intended to be used with NullBooleanField.
    """
    def __init__(self, attrs=None,true='Yes',false='No',none='--------'):
        choices = (('1', none),
                   ('2', true),
                   ('3', false))
        forms.widgets.Select.__init__(self,attrs, choices)

