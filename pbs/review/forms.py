from django import forms
from pbs.prescription.models import Region, District
from pbs.review.models import PrescribedBurn, Fire


class BurnStateSummaryForm(forms.Form):
    region = forms.ModelChoiceField(required=False, queryset=Region.objects.all())
    district = forms.ModelChoiceField(required=False, queryset=District.objects.all())


class PrescribedBurnForm(forms.ModelForm):
    region = forms.ModelChoiceField(required=False, queryset=Region.objects.all())
    district = forms.ModelChoiceField(required=False, queryset=District.objects.all())

    def __init__(self, *args, **kwargs):
        super(PrescribedBurnForm, self).__init__(*args, **kwargs)
        #import ipdb; ipdb.set_trace()
        if kwargs.has_key('initial') and kwargs['initial'].has_key('user'):
            self._user = kwargs['initial']['user']
            self.fields['user'] = kwargs['initial']['user']

        prescription = self.fields['prescription'].queryset
        #self.fields['prescription'].queryset = prescription.filter(region=1)
        self.fields['prescription'].queryset = prescription.all()

        #self.fields['prescription'].queryset = self.reviewed_prescriptions()

    def reviewed_prescriptions(self):
        """
        Filters prescriptions that have been reviewed by both FMSB and DRFMS
        """
        reviewed = []
        prescriptions = self.fields['prescription'].queryset
        for p in prescriptions: #Prescription.objects.all():
            if all(x in [i.review_type for i in p.burnstate.all()] for x in ['FMSB','DRFMS']):
                reviewed.append(p.id)
        return prescriptions.filter(id__in=reviewed)

    class Meta:
        model = PrescribedBurn


#    def __init__(self, *args, **kwargs):
#        super(PrescribedBurnForm, self).__init__(*args, **kwargs)
#        import ipdb; ipdb.set_trace()
#        #self._user = kwargs.pop('user')
#        if kwargs.has_key('initial') and kwargs['initial'].has_key('user'):
#            self._user = kwargs['initial']['user']
#            self.fields['user'] = kwargs['initial']['user']
#
#    #area = forms.DecimalField(widget=forms.HiddenInput(), initial=)
#    class Meta:
#        #model = PlannedBurn
#        exclude = ('user', )
#

class FireForm(forms.ModelForm):
    class Meta:
        model = Fire
        exclude = ('user', )


class FireLoadForm(forms.Form):
    region = forms.ModelChoiceField(required=False, queryset=Region.objects.all())
    district = forms.ModelChoiceField(required=False, queryset=District.objects.all())
    fire_type = forms.ChoiceField(required=False, choices=[(0, '------'), (1, 'Burns'), (2, 'Fires')])

