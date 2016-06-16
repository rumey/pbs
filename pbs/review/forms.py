from django import forms
from pbs.prescription.models import Prescription, Region, District
from pbs.review.models import PrescribedBurn
from datetime import datetime, timedelta
from django.conf import settings
from django.forms import ValidationError


class BurnStateSummaryForm(forms.Form):
    region = forms.ModelChoiceField(required=False, queryset=Region.objects.all())
    district = forms.ModelChoiceField(required=False, queryset=District.objects.all())


class PrescribedBurnForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(PrescribedBurnForm, self).__init__(*args, **kwargs)

        prescriptions = self.fields['prescription'].queryset
        self.fields['prescription'].queryset = prescriptions.filter(
            burnstate__review_type__in=['FMSB'], planning_status=Prescription.PLANNING_APPROVED).filter(burnstate__review_type__in=['DRFMS']).distinct().order_by('burn_id')
        self.fields['planned_area_unit'].required = True
        self.fields['planned_area'].required=True
        self.fields['location'].required = True
        self.fields['location'].widget.attrs.update({'placeholder': 'eg. 2 kms NorthEast of CBD'})

        planned_area_unit = self.fields['planned_area_unit']
        planned_area_unit.choices = planned_area_unit.choices[1:]

        now = datetime.now()
        today = now.date()
        tomorrow = today + timedelta(days=1)
        time_now = now.time()
        date_str = tomorrow.strftime('%Y-%m-%d') if time_now.hour > settings.DAY_ROLLOVER_HOUR else today.strftime('%Y-%m-%d')
        self.fields['date'].widget.attrs.update({'value': date_str})
        self.fields['est_start'].widget.attrs.update({'value': now.strftime('%H:%M')})
        self.initial['status'] = 1

    def clean(self):
        if self.cleaned_data.has_key('prescription') and self.cleaned_data.has_key('date'):
            # check for integrity constraint - duplicate keys
            prescription = self.cleaned_data['prescription']
            #region = self.cleaned_data['region']
            dt = self.cleaned_data['date']

            if dt > prescription.current_approval.valid_to:
                raise ValidationError("Date Error: Burn ID  {} is valid to {}".format(prescription.burn_id, prescription.current_approval.valid_to))

            objects = PrescribedBurn.objects.filter(prescription=prescription, date=dt, form_name=PrescribedBurn.FORM_268A)
            if objects:
                raise ValidationError("Burn ID  {}  already exists on this date".format(objects[0].prescription.burn_id))
            else:
                return self.cleaned_data

#    def clean_region(self):
#        import ipdb; ipdb.set_trace()
#        instance = getattr(self, 'instance', None)
#        if instance and instance.pk:
#            return instance.region
#        else:
#            return self.cleaned_data['region']


    class Meta:
        model = PrescribedBurn
        fields = ('prescription', 'date', 'external_assist', 'planned_area', 'planned_area_unit', 'tenures', 'location', 'est_start', 'conditions',)


class PrescribedBurnEditForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(PrescribedBurnEditForm, self).__init__(*args, **kwargs)

        #self.fields['region'].widget.attrs['disabled'] = 'disabled'
        self.fields['prescription'].widget.attrs['disabled'] = 'disabled'
        #self.fields['prescription'].widget.attrs['readonly'] = 'readonly'

        self.fields['location'].required = True
        self.fields['planned_area'].required = True
        self.fields['planned_area_unit'].required = True
        self.fields['location'].widget.attrs.update({'placeholder': 'eg. 2 kms NorthEast of CBD'})

        planned_area_unit = self.fields['planned_area_unit']
        planned_area_unit.choices = planned_area_unit.choices[1:]

    def clean_prescription(self):
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            return instance.prescription
        else:
            return self.cleaned_data['prescription']

    def clean_region(self):
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            return instance.region
        else:
            return self.cleaned_data['region']

    class Meta:
        model = PrescribedBurn
        #exclude = ('fire_id', 'fire_name', 'region', 'district', 'approval_268a_status', 'approval_268b_status', 'further_ignitions', 'form_name',)
        fields = ('prescription', 'date', 'external_assist', 'planned_area', 'planned_area_unit', 'tenures', 'location', 'est_start', 'conditions',)


class PrescribedBurnActiveForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(PrescribedBurnActiveForm, self).__init__(*args, **kwargs)

        prescriptions = self.fields['prescription'].queryset
        self.fields['prescription'].queryset = prescriptions.filter(
            burnstate__review_type__in=['FMSB'], planning_status=Prescription.PLANNING_APPROVED).filter(burnstate__review_type__in=['DRFMS']).distinct().order_by('burn_id')
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

        area_unit = self.fields['area_unit']
        area_unit.choices = area_unit.choices[1:]

        self.fields['prescription'].required = True
        self.fields['status'].required = True
        self.fields['area'].required = True
        self.fields['area_unit'].required = True

    def clean(self):
        if self.cleaned_data.has_key('prescription') and self.cleaned_data.has_key('date'):
            # check for integrity constraint - duplicate keys
            prescription = self.cleaned_data['prescription']
            dt = self.cleaned_data['date']
            objects = PrescribedBurn.objects.filter(prescription=prescription, date=dt, form_name=PrescribedBurn.FORM_268B)
            if objects:
                raise ValidationError("Burn ID  {}  already exists on this date".format(objects[0].prescription.burn_id))
            else:
                return self.cleaned_data

    class Meta:
        model = PrescribedBurn
        fields = ('prescription', 'date', 'status', 'ignition_status', 'external_assist', 'area', 'area_unit', 'tenures')


class PrescribedBurnEditActiveForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(PrescribedBurnEditActiveForm, self).__init__(*args, **kwargs)

        self.fields['prescription'].widget.attrs['disabled'] = 'disabled'
        self.fields['status'].label = 'Burn Status'

        now = datetime.now()
        today = now.date()
        tomorrow = today + timedelta(days=1)
        time_now = now.time()
        date_str = tomorrow.strftime('%Y-%m-%d') if time_now.hour > settings.DAY_ROLLOVER_HOUR else today.strftime('%Y-%m-%d')
        self.fields['date'].widget.attrs.update({'value': date_str})
        #self.initial['status'] = 1

        #status = self.fields['status']
        #status.choices = status.choices[1:]

        area_unit = self.fields['area_unit']
        area_unit.choices = area_unit.choices[1:]

        self.fields['status'].required = True
        self.fields['area'].required = True
        self.fields['area_unit'].required = True

    def clean_prescription(self):
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            return instance.prescription
        else:
            return self.cleaned_data['prescription']

#    def clean_region(self):
#        instance = getattr(self, 'instance', None)
#        if instance and instance.pk:
#            return instance.region
#        else:
#            return self.cleaned_data['region']

    class Meta:
        model = PrescribedBurn
        fields = ('prescription', 'date', 'status', 'ignition_status', 'external_assist', 'area', 'area_unit', 'tenures')




class FireForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(FireForm, self).__init__(*args, **kwargs)

        self.fields['region'].required = True
        self.fields['district'].required = True
        self.fields['fire_id'].required = True
        self.fields['fire_name'].required = True
        self.fields['status'].required = True
        self.fields['area'].required = True
        self.fields['area_unit'].required = True
        self.fields['area'].label = 'Area Burnt (ha)'
        self.fields['fire_id'].widget.attrs.update({'placeholder': 'Digits must be between 001-999'})
        now = datetime.now()
        today = now.date()
        tomorrow = today + timedelta(days=1)
        time_now = now.time()
        date_str = tomorrow.strftime('%Y-%m-%d') if time_now.hour > settings.DAY_ROLLOVER_HOUR else today.strftime('%Y-%m-%d')
        self.fields['date'].widget.attrs.update({'value': date_str})

        status = self.fields['status']
        status.choices = status.choices[1:]

        area_unit = self.fields['area_unit']
        area_unit.choices = area_unit.choices[1:]

    class Meta:
        model = PrescribedBurn
        fields = ('region', 'district', 'fire_id', 'fire_name', 'date', 'status', 'external_assist', 'area', 'area_unit', 'fire_tenures',)


class FireEditForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(FireEditForm, self).__init__(*args, **kwargs)
        self.initial['fire_id'] = self.initial['fire_id'][-3:]

        self.fields['fire_name'].required = True
        self.fields['status'].required = True
        self.fields['area'].required = True
        self.fields['area_unit'].required = True
        self.fields['area'].label = 'Area Burnt (ha)'

        self.fields['region'].widget.attrs['disabled'] = 'disabled'
        self.fields['district'].widget.attrs['disabled'] = 'disabled'
        self.fields['fire_id'].widget.attrs['disabled'] = 'disabled'

        area_unit = self.fields['area_unit']
        area_unit.choices = area_unit.choices[1:]

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
        fields = ('region', 'district', 'fire_id', 'fire_name', 'date', 'status', 'external_assist', 'area', 'area_unit', 'fire_tenures',)


class PrescribedBurnFilterForm(forms.ModelForm):
    approval_status = forms.ChoiceField(required=False, choices=PrescribedBurn.APPROVAL_CHOICES)

    class Meta:
        fields = ('region', 'district', 'approval_status')
        model = PrescribedBurn


class FireLoadFilterForm(forms.ModelForm):
    fire_type = forms.ChoiceField(required=False, choices=[(0, '------'), (1, 'Burns'), (2, 'Bushfires')])
    approval_status = forms.ChoiceField(required=False, choices=PrescribedBurn.APPROVAL_CHOICES)

    class Meta:
        fields = ('region', 'district', 'fire_type', 'approval_status')
        model = PrescribedBurn


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



