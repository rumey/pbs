from django import forms
from pbs.prescription.models import Prescription, Region, District
from pbs.review.models import PrescribedBurn, AircraftBurn
from datetime import datetime, timedelta
from django.conf import settings
from django.forms import ValidationError

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, ButtonHolder, Submit, Field, Div

class BurnStateSummaryForm(forms.Form):
    region = forms.ModelChoiceField(required=False, queryset=Region.objects.all())
    district = forms.ModelChoiceField(required=False, queryset=District.objects.all())


class PrescribedBurnForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(PrescribedBurnForm, self).__init__(*args, **kwargs)

#        prescriptions = self.fields['prescription'].queryset
#        self.fields['prescription'].queryset = prescriptions.filter(
#            burnstate__review_type__in=['FMSB'], planning_status=Prescription.PLANNING_APPROVED).filter(burnstate__review_type__in=['DRFMS']).distinct().order_by('burn_id')
        self.fields['prescription'].required = True
        self.fields['location'].required = True
        self.fields['location'].widget.attrs.update({'placeholder': 'eg. 2 kms NorthEast of CBD'})

        self.fields['planned_area'].widget.attrs.update({'placeholder': 'Enter hectares to 1 dec place'})
        self.fields['planned_distance'].widget.attrs.update({'placeholder': 'Enter kilometres to 1 dec place'})

        now = datetime.now()
        today = now.date()
        tomorrow = today + timedelta(days=1)
        time_now = now.time()
        date_str = tomorrow.strftime('%Y-%m-%d') if time_now.hour > settings.DAY_ROLLOVER_HOUR else today.strftime('%Y-%m-%d')
        self.fields['date'].widget.attrs.update({'value': date_str})
        self.fields['est_start'].widget.attrs.update({'value': now.strftime('%H:%M')})
        self.initial['status'] = 1

    def clean(self):

        if not self.cleaned_data.has_key('prescription'):
            raise ValidationError("Prescription is Required")

        if not (self.cleaned_data['planned_area'] or self.cleaned_data['planned_distance']):
            raise ValidationError("Must input at least one of Area or Distance")

        if not self.cleaned_data.has_key('location'):
            raise ValidationError("Must input location")

        if self.cleaned_data.has_key('prescription') and self.cleaned_data.has_key('date') and self.cleaned_data.has_key('location'):
            # check for integrity constraint - duplicate keys
            prescription = self.cleaned_data['prescription']
            dt = self.cleaned_data['date']
            location = self.cleaned_data['location']

            if hasattr(prescription, "current_approval") and dt > prescription.current_approval.valid_to:
                raise ValidationError("Date Error: Burn ID  {} is valid to {}".format(prescription.burn_id, prescription.current_approval.valid_to))

            objects = PrescribedBurn.objects.filter(prescription=prescription, date=dt, form_name=PrescribedBurn.FORM_268A, location=location)
            if objects:
                raise ValidationError("Burn ID  {}  already exists on this date, with this location".format(objects[0].prescription.burn_id))
            else:
                return self.cleaned_data

    class Meta:
        model = PrescribedBurn
        fields = ('region', 'prescription', 'date', 'planned_area',
                  'planned_distance', 'tenures', 'location', 'est_start', 'conditions',
                 )


class PrescribedBurnEditForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(PrescribedBurnEditForm, self).__init__(*args, **kwargs)
        prescribed_burn = kwargs.get('instance')

        # hack to get the instance choices (region and prescription) to display read-only/disabled
        region = self.fields['region']
        region_idx = [i[0] for i in region.choices if prescribed_burn.get_region_display()==i[1]][0]
        region.choices = [region.choices[region_idx]]
        self.fields['region'].widget.attrs['disabled'] = 'disabled'

        prescription = self.fields['prescription']
        self.fields['prescription'].queryset = prescription.queryset.filter(burn_id=prescribed_burn.fire_idd)
        self.fields['prescription'].widget.attrs['readonly'] = True

        self.fields['location'].required = True
        self.fields['location'].widget.attrs.update({'placeholder': 'eg. 2 kms NorthEast of CBD'})

        self.fields['planned_area'].widget.attrs.update({'placeholder': 'Enter hectares to 1 dec place'})
        self.fields['planned_distance'].widget.attrs.update({'placeholder': 'Enter kilometres to 1 dec place'})

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

    def clean_location(self):

        if self.cleaned_data.has_key('prescription') and self.cleaned_data.has_key('date'):
            # check for integrity constraint - duplicate keys
            prescription = self.cleaned_data['prescription']
            dt = self.cleaned_data['date']
            location = self.cleaned_data['location']

            if hasattr(prescription, "current_approval") and dt > prescription.current_approval.valid_to:
                raise ValidationError("Date Error: Burn ID  {} is valid to {}".format(prescription.burn_id, prescription.current_approval.valid_to))

            objects = PrescribedBurn.objects.filter(prescription=prescription, date=dt, form_name=PrescribedBurn.FORM_268A, location=location)
            if objects and objects[0] != getattr(self, 'instance', None):
                raise ValidationError("Burn ID  {}  already exists on this date, with this location".format(objects[0].prescription.burn_id))
            else:
                return self.cleaned_data['location']

    class Meta:
        model = PrescribedBurn
        fields = ('region', 'prescription', 'date', 'planned_area',
                  'planned_distance', 'tenures', 'location', 'est_start', 'conditions',
                 )


class PrescribedBurnActiveForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(PrescribedBurnActiveForm, self).__init__(*args, **kwargs)

#        prescriptions = self.fields['prescription'].queryset
#        self.fields['prescription'].queryset = prescriptions.filter(
#            burnstate__review_type__in=['FMSB'], planning_status=Prescription.PLANNING_APPROVED).filter(burnstate__review_type__in=['DRFMS']).distinct().order_by('burn_id')

        now = datetime.now()
        today = now.date()
        tomorrow = today + timedelta(days=1)
        time_now = now.time()
        date_str = tomorrow.strftime('%Y-%m-%d') if time_now.hour > settings.DAY_ROLLOVER_HOUR else today.strftime('%Y-%m-%d')
        self.fields['date'].widget.attrs.update({'value': date_str})
        #self.initial['status'] = 1

        self.fields['prescription'].required = True
        self.fields['status'].required = True

        self.fields['area'].widget.attrs.update({'placeholder': 'Enter hectares to 1 dec place'})
        self.fields['distance'].widget.attrs.update({'placeholder': 'Enter kilometres to 1 dec place'})

    def clean(self):
        if self.cleaned_data['area']==None and self.cleaned_data['distance']==None:
            raise ValidationError("Must input at least one of Area or Distance")

        if self.cleaned_data.has_key('prescription') and self.cleaned_data.has_key('date'):
            # check for integrity constraint - duplicate keys
            prescription = self.cleaned_data['prescription']
            dt = self.cleaned_data['date']
            #location = self.cleaned_data['location']

            #objects = PrescribedBurn.objects.filter(prescription=prescription, date=dt, form_name=PrescribedBurn.FORM_268B, location=location)
            objects = PrescribedBurn.objects.filter(prescription=prescription, date=dt, form_name=PrescribedBurn.FORM_268B)
            if objects:
                raise ValidationError("Burn ID  {}  already exists on this date".format(objects[0].prescription.burn_id))
            else:
                return self.cleaned_data

    class Meta:
        model = PrescribedBurn
        fields = ('region', 'prescription', 'date', 'status', 'ignition_status', 'area', 'distance', 'tenures',)


class PrescribedBurnEditActiveForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(PrescribedBurnEditActiveForm, self).__init__(*args, **kwargs)
        prescribed_burn = kwargs.get('instance')

        # hack to get the instance choices (region and prescription) to display read-only/disabled
        region = self.fields['region']
        region_idx = [i[0] for i in region.choices if prescribed_burn.get_region_display()==i[1]][0]
        region.choices = [region.choices[region_idx]]
        self.fields['region'].widget.attrs['disabled'] = 'disabled'

        prescription = self.fields['prescription']
        self.fields['prescription'].queryset = prescription.queryset.filter(burn_id=prescribed_burn.fire_idd)
        self.fields['prescription'].widget.attrs['readonly'] = True

        #status = self.fields['status']
        #status.choices = status.choices[1:]
        self.initial['status'] = 0

        now = datetime.now()
        today = now.date()
        tomorrow = today + timedelta(days=1)
        time_now = now.time()
        date_str = tomorrow.strftime('%Y-%m-%d') if time_now.hour > settings.DAY_ROLLOVER_HOUR else today.strftime('%Y-%m-%d')
        self.fields['date'].widget.attrs.update({'value': date_str})

        self.fields['status'].required = True

        self.fields['area'].widget.attrs.update({'placeholder': 'Enter hectares to 1 dec place'})
        self.fields['distance'].widget.attrs.update({'placeholder': 'Enter kilometres to 1 dec place'})

    def clean_prescription(self):
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            return instance.prescription
        else:
            return self.cleaned_data['prescription']

#    def clean_location(self):
#
#        if self.cleaned_data.has_key('prescription') and self.cleaned_data.has_key('date'):
#            # check for integrity constraint - duplicate keys
#            prescription = self.cleaned_data['prescription']
#            dt = self.cleaned_data['date']
#            location = self.cleaned_data['location']
#
#            if hasattr(prescription, "current_approval") and dt > prescription.current_approval.valid_to:
#                raise ValidationError("Date Error: Burn ID  {} is valid to {}".format(prescription.burn_id, prescription.current_approval.valid_to))
#
#            objects = PrescribedBurn.objects.filter(prescription=prescription, date=dt, form_name=PrescribedBurn.FORM_268B, location=location)
#            if objects:
#                raise ValidationError("Burn ID  {}  already exists on this date, with this location".format(objects[0].prescription.burn_id))
#            else:
#                return self.cleaned_data['location']

    class Meta:
        model = PrescribedBurn
        fields = ('region', 'prescription', 'date', 'status', 'ignition_status', 'area', 'distance', 'tenures',)


class FireForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(FireForm, self).__init__(*args, **kwargs)

        self.fields['region'].required = True
        self.fields['district'].required = True
        self.fields['fire_id'].required = True
        self.fields['fire_name'].required = True
        self.fields['status'].required = True
        self.fields['area'].required = True
        self.fields['area'].label = 'Area Burnt (ha)'
        self.fields['fire_id'].widget.attrs.update({'placeholder': 'Digits must be between 001-999'})
        now = datetime.now()
        today = now.date()
        tomorrow = today + timedelta(days=1)
        time_now = now.time()
        date_str = tomorrow.strftime('%Y-%m-%d') if time_now.hour > settings.DAY_ROLLOVER_HOUR else today.strftime('%Y-%m-%d')
        self.fields['date'].widget.attrs.update({'value': date_str})

        self.fields['area'].widget.attrs.update({'placeholder': 'Enter hectares to 1 dec place'})

    class Meta:
        model = PrescribedBurn
        fields = ('region', 'district', 'fire_id', 'fire_name', 'date', 'status', 'external_assist', 'area', 'fire_tenures',)


class FireEditForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(FireEditForm, self).__init__(*args, **kwargs)
        prescribed_burn = kwargs.get('instance')
        self.initial['fire_id'] = self.initial['fire_id'][-3:]

        self.fields['fire_name'].required = True
        self.fields['status'].required = True
        self.fields['area'].required = True
        self.fields['area'].label = 'Area Burnt (ha)'

        # hack to get the instance choices (region and district) to display read-only/disabled
        region = self.fields['region']
        region_idx = [i[0] for i in region.choices if prescribed_burn.get_region_display()==i[1]][0]
        region.choices = [region.choices[region_idx]]
        self.fields['region'].widget.attrs['disabled'] = 'disabled'

        district = self.fields['district']
        self.fields['district'].queryset = district.queryset.filter(name=prescribed_burn.district)
        self.fields['district'].widget.attrs['readonly'] = True

        self.fields['fire_id'].widget.attrs['readonly'] = True

        status = self.fields['status']
        status.choices = status.choices[1:]

        self.fields['area'].widget.attrs.update({'placeholder': 'Enter hectares to 1 dec place'})

    def clean_region(self):
        """
        need this when widget is disabled
        """
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            return instance.region
        else:
            return self.cleaned_data['region']

#    def clean_district(self):
#        instance = getattr(self, 'instance', None)
#        if instance and instance.pk:
#            return instance.district
#        else:
#            return self.cleaned_data['district']

    def clean_fire_id(self):
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            return instance.fire_id
        else:
            return self.cleaned_data['fire_id']

    class Meta:
        model = PrescribedBurn
        fields = ('region', 'district', 'fire_id', 'fire_name', 'date', 'status', 'external_assist', 'area', 'fire_tenures',)


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


class AircraftBurnFilterForm(forms.ModelForm):
    region = forms.ModelChoiceField(required=False, queryset=Region.objects.all())
    approval_status = forms.ChoiceField(required=False, choices=PrescribedBurn.APPROVAL_CHOICES)

    class Meta:
        fields = ('region', 'approval_status')
        model = AircraftBurn


class AircraftBurnForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(AircraftBurnForm, self).__init__(*args, **kwargs)

    class Meta:
        #exlude = ('flight_seq', 'aircraft_rego', 'arrival_time', 'program',)
        fields = ('prescription', 'date', 'area', 'est_start', 'bombing_duration', 'min_smc', 'max_fdi', 'sdi_per_day', 'aircrew')
        model = AircraftBurn


class AircraftBurnEditForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(AircraftBurnEditForm, self).__init__(*args, **kwargs)

    class Meta:
        fields = ('prescription', 'date', 'area', 'est_start', 'bombing_duration', 'min_smc', 'max_fdi', 'sdi_per_day',
                  'flight_seq', 'aircraft_rego', 'arrival_time', 'program', 'aircrew'
            )
        model = AircraftBurn


