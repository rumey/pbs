from django import forms
from pbs.prescription.models import Region, District
from pbs.review.models import PrescribedBurn, Fire
from datetime import datetime, timedelta
from django.conf import settings


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

        prescriptions = self.fields['prescription'].queryset
        #self.fields['prescription'].queryset = prescriptions.filter(region=1)
        self.fields['prescription'].queryset = prescriptions.all()
        self.fields['location'].widget.attrs.update({'placeholder': 'eg. 2 kms NorthEast of CBD'})

        now = datetime.now()
        today = now.date()
        tomorrow = today + timedelta(days=1)
        time_now = now.time()
        date_str = tomorrow.strftime('%Y-%m-%d') if time_now.hour > settings.DAY_ROLLOVER_HOUR else today.strftime('%Y-%m-%d')
        #self.fields['date'].widget = forms.HiddenInput()
        #self.fields['date'].widget.attrs['readonly'] = True
        #self.fields['date'].widget.attrs['disabled'] = True
        self.fields['date'].widget.attrs.update({'value': date_str})
        self.fields['est_start'].widget.attrs.update({'value': now.strftime('%H:%M')})
        self.initial['status'] = 1
        #self.fields['location'].queryset = prescription.location
        #self.fields['region'].widget = forms.HiddenInput()
        #self.fields['district'].widget = forms.HiddenInput()

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

#    def save(self):
#        now = datetime.now()
#        today = now.date()
#        time_now = now.time()
#
#        import ipdb; ipdb.set_trace()
#        self.fields['date'] = today.strftime('%Y-%m-%d')
#        super(PrescribedBurnForm, self).save()

    class Meta:
        model = PrescribedBurn
        exclude = ('area','region', 'district', 'submitted_by', 'endorsed_by', 'approved_by', 'approval_status', 'rolled',)
        #fields = ("prescription", "date", "status", "further_ignitions", "external_assist", "planned_area", "tenures", "location", "est_start", "conditions")

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
class PrescribedBurnEditForm(forms.ModelForm):
    region = forms.ModelChoiceField(required=False, queryset=Region.objects.all())
    district = forms.ModelChoiceField(required=False, queryset=District.objects.all())

    def __init__(self, *args, **kwargs):
        super(PrescribedBurnEditForm, self).__init__(*args, **kwargs)
        #import ipdb; ipdb.set_trace()
        if kwargs.has_key('initial') and kwargs['initial'].has_key('user'):
            self._user = kwargs['initial']['user']
            self.fields['user'] = kwargs['initial']['user']

        prescriptions = self.fields['prescription'].queryset
        #self.fields['prescription'].queryset = prescriptions.filter(region=1)
        self.fields['prescription'].queryset = prescriptions.all()
        self.fields['location'].widget.attrs.update({'placeholder': 'eg. 2 kms NorthEast of CBD'})

        now = datetime.now()
        today = now.date()
        tomorrow = today + timedelta(days=1)
        time_now = now.time()
        date_str = tomorrow.strftime('%Y-%m-%d') if time_now.hour > settings.DAY_ROLLOVER_HOUR else today.strftime('%Y-%m-%d')
        #self.fields['date'].widget.attrs.update({'value': date_str})
        #self.fields['est_start'].widget.attrs.update({'value': now.strftime('%H:%M')})
        #self.initial['status'] = 1
    class Meta:
        model = PrescribedBurn
        exclude = ('region', 'district', 'submitted_by', 'endorsed_by', 'approved_by', 'approval_status', 'rolled',)

class FireForm(forms.ModelForm):
    class Meta:
        model = Fire
        exclude = ('user', )


class PrescribedBurnFilterForm(forms.Form):
    region = forms.ModelChoiceField(required=False, queryset=Region.objects.all())
    district = forms.ModelChoiceField(required=False, queryset=District.objects.all())


class FireLoadFilterForm(forms.Form):
    region = forms.ModelChoiceField(required=False, queryset=Region.objects.all())
    district = forms.ModelChoiceField(required=False, queryset=District.objects.all())
    fire_type = forms.ChoiceField(required=False, choices=[(0, '------'), (1, 'Burns'), (2, 'Fires')])

