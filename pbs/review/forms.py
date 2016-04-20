from django import forms
from pbs.prescription.models import Region, District
from pbs.review.models import PlannedBurn, PrescribedBurn, Fire


class BurnStateSummaryForm(forms.Form):
    region = forms.ModelChoiceField(required=False, queryset=Region.objects.all())
    district = forms.ModelChoiceField(required=False, queryset=District.objects.all())

#class PlannedBurnSummaryForm(forms.Form):
#    date = forms.DateField(required=False)
#    region = forms.ModelChoiceField(required=False, queryset=Region.objects.all())
#    district = forms.ModelChoiceField(required=False, queryset=District.objects.all())
#
#    def clean_fromDate(self):
#        d = self.cleaned_data.get('fromDate')
#        if d is None:
#            d = date(1970, 1, 1)
#        return d
#
#    def clean_toDate(self):
#        d = self.cleaned_data.get('toDate')
#        if d is None:
#            d = date.today()
#        return d


class PlannedBurnForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(PlannedBurnForm, self).__init__(*args, **kwargs)
        import ipdb; ipdb.set_trace()
        #self._user = kwargs.pop('user')
        if kwargs.has_key('initial') and kwargs['initial'].has_key('user'):
            self._user = kwargs['initial']['user']
            self.fields['user'] = kwargs['initial']['user']

    #area = forms.DecimalField(widget=forms.HiddenInput(), initial=)
    class Meta:
        model = PlannedBurn
        exclude = ('user', )


class FireForm(forms.ModelForm):
    class Meta:
        model = Fire
        exclude = ('user', )


class FireLoadForm(forms.Form):
    region = forms.ModelChoiceField(required=False, queryset=Region.objects.all())
    district = forms.ModelChoiceField(required=False, queryset=District.objects.all())
    fire_type = forms.ChoiceField(required=False, choices=[(0, '------'), (1, 'Burns'), (2, 'Fires')])

