from django import forms
from pbs.prescription.models import Region, District
from pbs.review.models import PrescribedBurn
from datetime import datetime, timedelta
from django.conf import settings


class BurnStateSummaryForm(forms.Form):
    region = forms.ModelChoiceField(required=False, queryset=Region.objects.all())
    district = forms.ModelChoiceField(required=False, queryset=District.objects.all())


class PrescribedBurnForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(PrescribedBurnForm, self).__init__(*args, **kwargs)

        prescriptions = self.fields['prescription'].queryset
        self.fields['prescription'].queryset = prescriptions.filter(burnstate__review_type__in=['FMSB','DRFMS']).distinct().order_by('burn_id')
        self.fields['planned_area'].required=True
        self.fields['location'].widget.attrs.update({'placeholder': 'eg. 2 kms NorthEast of CBD'})

        now = datetime.now()
        today = now.date()
        tomorrow = today + timedelta(days=1)
        time_now = now.time()
        date_str = tomorrow.strftime('%Y-%m-%d') if time_now.hour > settings.DAY_ROLLOVER_HOUR else today.strftime('%Y-%m-%d')
        self.fields['date'].widget.attrs.update({'value': date_str})
        self.fields['est_start'].widget.attrs.update({'value': now.strftime('%H:%M')})
        self.initial['status'] = 1

    class Meta:
        model = PrescribedBurn
        exclude = ('fire_id', 'fire_name', 'region', 'district', 'status', 'area', 'approval_268a_status', 'approval_268b_status', 'further_ignitions', 'form_name',)


class PrescribedBurnEditForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(PrescribedBurnEditForm, self).__init__(*args, **kwargs)

        self.fields['prescription'].widget.attrs['disabled'] = 'disabled'
        #self.fields['prescription'].widget.attrs['readonly'] = 'readonly'

        self.fields['location'].widget.attrs.update({'placeholder': 'eg. 2 kms NorthEast of CBD'})
        self.fields['status'].label = 'Burn Status'

        status = self.fields['status']
        status.choices = status.choices[1:]

    def clean_prescription(self):
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            return instance.prescription
        else:
            return self.cleaned_data['prescription']

    class Meta:
        model = PrescribedBurn
        exclude = ('fire_id', 'fire_name', 'region', 'district', 'approval_268a_status', 'approval_268b_status', 'further_ignitions', 'form_name',)


class PrescribedBurnActiveForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(PrescribedBurnActiveForm, self).__init__(*args, **kwargs)

        prescriptions = self.fields['prescription'].queryset
        self.fields['prescription'].queryset = prescriptions.filter(burnstate__review_type__in=['FMSB','DRFMS']).distinct().order_by('burn_id')
        self.fields['location'].widget.attrs.update({'placeholder': 'eg. 2 kms NorthEast of CBD'})
        self.fields['status'].label = 'Burn Status'

        now = datetime.now()
        today = now.date()
        tomorrow = today + timedelta(days=1)
        time_now = now.time()
        date_str = tomorrow.strftime('%Y-%m-%d') if time_now.hour > settings.DAY_ROLLOVER_HOUR else today.strftime('%Y-%m-%d')
        self.fields['date'].widget.attrs.update({'value': date_str})
        self.initial['status'] = 1

        status = self.fields['status']
        status.choices = status.choices[1:]

        self.fields['prescription'].required = True
        self.fields['status'].required = True
        self.fields['area'].required = True
        self.fields['location'].required = True

    class Meta:
        model = PrescribedBurn
        fields = ('prescription', 'date', 'status', 'external_assist', 'area', 'tenures', 'location', 'conditions',)


class PrescribedBurnEditActiveForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(PrescribedBurnEditActiveForm, self).__init__(*args, **kwargs)

        self.fields['prescription'].widget.attrs['disabled'] = 'disabled'
        self.fields['location'].widget.attrs.update({'placeholder': 'eg. 2 kms NorthEast of CBD'})
        self.fields['status'].label = 'Burn Status'

        now = datetime.now()
        today = now.date()
        tomorrow = today + timedelta(days=1)
        time_now = now.time()
        date_str = tomorrow.strftime('%Y-%m-%d') if time_now.hour > settings.DAY_ROLLOVER_HOUR else today.strftime('%Y-%m-%d')
        self.fields['date'].widget.attrs.update({'value': date_str})
        self.initial['status'] = 1

        status = self.fields['status']
        status.choices = status.choices[1:]

        self.fields['status'].required = True
        self.fields['area'].required = True
        self.fields['location'].required = True

    def clean_prescription(self):
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            return instance.prescription
        else:
            return self.cleaned_data['prescription']

    class Meta:
        model = PrescribedBurn
        fields = ('prescription', 'date', 'status', 'external_assist', 'area', 'tenures', 'location', 'conditions',)




class FireForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(FireForm, self).__init__(*args, **kwargs)
        self.fields['location'].widget.attrs.update({'placeholder': 'eg. 2 kms NorthEast of CBD'})

        self.fields['region'].required = True
        self.fields['district'].required = True
        self.fields['fire_id'].required = True
        self.fields['fire_name'].required = True
        self.fields['status'].required = True
        self.fields['location'].required = True
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
        fields = ('region', 'district', 'fire_id', 'fire_name', 'date', 'status', 'external_assist', 'area', 'tenures', 'location', 'conditions',)


class FireEditForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(FireEditForm, self).__init__(*args, **kwargs)
        self.initial['fire_id'] = self.initial['fire_id'][-3:]

        self.fields['fire_name'].required = True
        self.fields['status'].required = True
        self.fields['location'].required = True
        self.fields['area'].label = 'Area Burnt (ha)'

        self.fields['region'].widget.attrs['disabled'] = 'disabled'
        self.fields['district'].widget.attrs['disabled'] = 'disabled'
        self.fields['fire_id'].widget.attrs['disabled'] = 'disabled'

    def clean_region(self):
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            return instance.region
        else:
            return self.cleaned_data['region']

    def clean_district(self):
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            return instance.district
        else:
            return self.cleaned_data['district']

    def clean_fire_id(self):
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            return instance.fire_id
        else:
            return self.cleaned_data['fire_id']

    class Meta:
        model = PrescribedBurn
        fields = ('region', 'district', 'fire_id', 'fire_name', 'date', 'status', 'external_assist', 'area', 'tenures', 'location', 'conditions',)


class PrescribedBurnFilterForm(forms.Form):
    region = forms.ModelChoiceField(required=False, queryset=Region.objects.all())
    district = forms.ModelChoiceField(required=False, queryset=District.objects.all())
    approval_status = forms.ChoiceField(required=False, choices=PrescribedBurn.APPROVAL_CHOICES)


class FireLoadFilterForm(forms.Form):
    region = forms.ModelChoiceField(required=False, queryset=Region.objects.all())
    district = forms.ModelChoiceField(required=False, queryset=District.objects.all())
    fire_type = forms.ChoiceField(required=False, choices=[(0, '------'), (1, 'Burns'), (2, 'Fires')])
    approval_status = forms.ChoiceField(required=False, choices=PrescribedBurn.APPROVAL_CHOICES)


class FireFormSet(forms.ModelForm):
    class Meta:
        model = PrescribedBurn
        exclude = ('prescription', )

class CsvForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(CsvForm, self).__init__(*args, **kwargs)
        self.fields['fromDate'].label = 'ha)'

        now = datetime.now()
        toDate = now.date().strftime('%Y-%m-%d')
        fromDate = (now - timedelta(days=14)).strftime('%Y-%m-%d')
        self.fields['fromDate'].widget.attrs.update({'value': fromDate})
        self.fields['toDate'].widget.attrs.update({'value': toDate})

    fromDate = forms.DateField(required=False)
    toDate = forms.DateField(required=True)



