from django import forms
from pbs.prescription.models import Region, District


class BurnStateSummaryForm(forms.Form):
    region = forms.ModelChoiceField(required=False,
        queryset=Region.objects.all())
    district = forms.ModelChoiceField(required=False, queryset=District.objects.all())

