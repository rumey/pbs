from django import forms
from pbs.prescription.models import Region, District
from pbs.review.models import PrescribedBurn
from datetime import datetime, timedelta
from django.conf import settings


class BurnStateSummaryForm(forms.Form):
    region = forms.ModelChoiceField(required=False, queryset=Region.objects.all())
    district = forms.ModelChoiceField(required=False, queryset=District.objects.all())


class PrescribedBurnForm(forms.ModelForm):
    #region = forms.ModelChoiceField(required=False, queryset=Region.objects.all())
    #district = forms.ModelChoiceField(required=False, queryset=District.objects.all())

    def __init__(self, *args, **kwargs):
        super(PrescribedBurnForm, self).__init__(*args, **kwargs)
        if kwargs.has_key('initial') and kwargs['initial'].has_key('user'):
            self._user = kwargs['initial']['user']
            self.fields['user'] = kwargs['initial']['user']

        prescriptions = self.fields['prescription'].queryset
        #self.fields['prescription'].queryset = prescriptions.filter(region=1)
        #self.fields['prescription'].queryset = prescriptions.all()
        self.fields['prescription'].queryset = prescriptions.filter(burnstate__review_type__in=['FMSB','DRFMS'])
        self.fields['planned_area'].required=True
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

#        status = self.fields['status']
#        status.choices = status.choices[1:]

    class Meta:
        model = PrescribedBurn
        exclude = ('fire_id', 'fire_name', 'region', 'district', 'status', 'area', 'approval_268a_status', 'approval_268b_status', 'further_ignitions', 'form_name',)


class PrescribedBurnActiveForm(forms.ModelForm):
    #region = forms.ModelChoiceField(required=False, queryset=Region.objects.all())
    #district = forms.ModelChoiceField(required=False, queryset=District.objects.all())

    def __init__(self, *args, **kwargs):
        super(PrescribedBurnActiveForm, self).__init__(*args, **kwargs)
        if kwargs.has_key('initial') and kwargs['initial'].has_key('user'):
            self._user = kwargs['initial']['user']
            self.fields['user'] = kwargs['initial']['user']

        prescriptions = self.fields['prescription'].queryset
        #self.fields['prescription'].queryset = prescriptions.filter(region=1)
        #self.fields['prescription'].queryset = prescriptions.all()
        self.fields['prescription'].queryset = prescriptions.filter(burnstate__review_type__in=['FMSB','DRFMS'])
        #self.fields['planned_area'].required=True
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
        #self.fields['est_start'].widget.attrs.update({'value': now.strftime('%H:%M')})
        self.initial['status'] = 1

        status = self.fields['status']
        status.choices = status.choices[1:]

    def reviewed_prescriptions(self):
        """
        Filters prescriptions that have been reviewed by both FMSB and DRFMS
        """
        prescriptions = self.fields['prescription'].queryset
        return prescriptions.filter(burnstate__review_type__in=['FMSB','DRFMS'])

    class Meta:
        model = PrescribedBurn
        exclude = ('fire_id', 'fire_name', 'region', 'district', 'planned_area', 'est_start', 'approval_268a_status', 'approval_268b_status', 'further_ignitions', 'form_name',)


class PrescribedBurnEditForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(PrescribedBurnEditForm, self).__init__(*args, **kwargs)

        prescriptions = self.fields['prescription'].queryset
        #self.fields['prescription'].queryset = prescriptions.filter(region=1)
        self.fields['prescription'].queryset = prescriptions.all()
        self.fields['location'].widget.attrs.update({'placeholder': 'eg. 2 kms NorthEast of CBD'})
        self.fields['status'].label = 'Burn Status'

        now = datetime.now()
        today = now.date()
        tomorrow = today + timedelta(days=1)
        time_now = now.time()
        date_str = tomorrow.strftime('%Y-%m-%d') if time_now.hour > settings.DAY_ROLLOVER_HOUR else today.strftime('%Y-%m-%d')

        status = self.fields['status']
        status.choices = status.choices[1:]

    class Meta:
        model = PrescribedBurn
        exclude = ('fire_id', 'fire_name', 'region', 'district', 'approval_268a_status', 'approval_268b_status', 'further_ignitions', 'form_name',)


class FireForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(FireForm, self).__init__(*args, **kwargs)
        #import ipdb; ipdb.set_trace()
        self.fields['location'].widget.attrs.update({'placeholder': 'eg. 2 kms NorthEast of CBD'})

        self.fields['region'].required = True
        self.fields['district'].required = True
        self.fields['fire_id'].required = True
        self.fields['fire_name'].required = True
        self.fields['area'].label = 'Area Burnt (ha)'
        now = datetime.now()
        today = now.date()
        tomorrow = today + timedelta(days=1)
        time_now = now.time()
        date_str = tomorrow.strftime('%Y-%m-%d') if time_now.hour > settings.DAY_ROLLOVER_HOUR else today.strftime('%Y-%m-%d')
        self.fields['date'].widget.attrs.update({'value': date_str})

        status = self.fields['status']
        status.choices = status.choices[1:]

    class Meta:
        model = PrescribedBurn
        #exclude = ('prescription', 'status', 'further_ignitions', 'planned_area', 'est_start', 'approval_status', 'form_name',)
        fields = ('region', 'district', 'fire_id', 'fire_name', 'date', 'status', 'external_assist', 'area', 'tenures', 'location', 'conditions',)


class FireEditForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(FireEditForm, self).__init__(*args, **kwargs)
        #self.fields['fire_id'].widget.attrs['readonly'] = True
        #self.fields['fire_id'].widget.attrs['disabled'] = True
        self.initial['fire_id'] = self.initial['fire_id'][-3:]

    class Meta:
        model = PrescribedBurn
#        exclude = ('prescription', 'status', 'further_ignitions', 'planned_area', 'est_start', 'approval_status', 'form_name',)
        fields = ('region', 'district', 'fire_name', 'fire_id', 'date', 'status', 'external_assist', 'area', 'tenures', 'location', 'conditions',)


class PrescribedBurnFilterForm(forms.Form):
    region = forms.ModelChoiceField(required=False, queryset=Region.objects.all())
    district = forms.ModelChoiceField(required=False, queryset=District.objects.all())
    approval_status = forms.ChoiceField(required=False, choices=PrescribedBurn.APPROVAL_CHOICES)


class FireLoadFilterForm(forms.Form):
    region = forms.ModelChoiceField(required=False, queryset=Region.objects.all())
    district = forms.ModelChoiceField(required=False, queryset=District.objects.all())
    fire_type = forms.ChoiceField(required=False, choices=[(0, '------'), (1, 'Burns'), (2, 'Fires')])
    approval_status = forms.ChoiceField(required=False, choices=PrescribedBurn.APPROVAL_CHOICES)

#class FireForm(forms.ModelForm):
#    class Meta:
#        model = Fire

class FireFormSet(forms.ModelForm):
    class Meta:
        model = PrescribedBurn
        exclude = ('prescription', )

