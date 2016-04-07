from django import forms
from pbs.prescription.models import Region, District


class BurnStateSummaryForm(forms.Form):
    region = forms.ModelChoiceField(required=False, queryset=Region.objects.all())
    district = forms.ModelChoiceField(required=False, queryset=District.objects.all())

class PlannedBurnSummaryForm(forms.Form):
    date = forms.DateField(required=False)

    def clean_fromDate(self):
        d = self.cleaned_data.get('fromDate')
        if d is None:
            d = date(1970, 1, 1)
        return d

    def clean_toDate(self):
        d = self.cleaned_data.get('toDate')
        if d is None:
            d = date.today()
        return d


