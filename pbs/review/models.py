#from django.db import models
from swingers import models
from datetime import datetime, date, timedelta
from django.contrib.auth.models import User
from pbs.prescription.models import (Prescription, Region, District, Tenure)
from smart_selects.db_fields import ChainedForeignKey
from swingers.models.auth import Audit
from dateutil import tz
from django.utils.encoding import python_2_unicode_compatible

from django.core.validators import MaxValueValidator, MinValueValidator
from django.forms import ValidationError


class BurnState(models.Model):
    prescription = models.ForeignKey(Prescription, related_name='burnstate')
    user = models.ForeignKey(User, help_text="User")
    review_type = models.CharField(max_length=64)
    review_date = models.DateTimeField(auto_now_add=True)

    fmt = "%d/%m/%Y %H:%M:%S"

    @property
    def record(self):
        username = '{} {}'.format(self.user.first_name[0], self.user.last_name)
        return "{} {}".format(
            username, self.review_date.astimezone(tz.tzlocal()).strftime(self.fmt)
        )

    def __str__(self):
        return "{} - {} - {}".format(
            self.prescription, self.review_type, self.record)


@python_2_unicode_compatible
class ExternalAssist(models.Model):
    name = models.CharField(max_length=25)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class FireTenure(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Acknowledgement(models.Model):
    burn = models.ForeignKey('PrescribedBurn', related_name='acknowledgements')
    user = models.ForeignKey(User, help_text="User", null=True, blank=True)
    acknow_type = models.CharField(max_length=64, null=True, blank=True)
    acknow_date = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    fmt = "%d/%m/%Y %H:%M"

    @property
    def record(self):
        username = '{} {}'.format(self.user.first_name[0], self.user.last_name)
        return "{} {}".format(
            username, self.acknow_date.astimezone(tz.tzlocal()).strftime(self.fmt)
        )

    def remove(self):
        self.delete()

    def __str__(self):
        return "{} - {} - {}".format(
            self.burn, self.acknow_type, self.record)


@python_2_unicode_compatible
class PrescribedBurn(Audit):
    BURN_ACTIVE = 1
    BURN_INACTIVE = 2
    BURN_CHOICES = (
        (BURN_ACTIVE, 'Yes'),
        (BURN_INACTIVE, 'No'),
    )

    IGNITION_STATUS_REQUIRED = 1
    IGNITION_STATUS_COMPLETED = 2
    IGNITION_STATUS_CHOICES = (
        (IGNITION_STATUS_REQUIRED, 'Further ignitions required'),
        (IGNITION_STATUS_COMPLETED, 'Ignition now complete'),
    )

    APPROVAL_DRAFT = 'DRAFT'
    APPROVAL_SUBMITTED = 'USER'
    APPROVAL_ENDORSED = 'SRM'
    APPROVAL_APPROVED = 'SDO'
    APPROVAL_CHOICES = (
        (APPROVAL_DRAFT, 'Draft'),
        (APPROVAL_SUBMITTED, 'District Submitted'),
        (APPROVAL_ENDORSED, 'Region Endorsed'),
        (APPROVAL_APPROVED, 'State Approved'),
    )

    FORM_268A = 1
    FORM_268B = 2
    FORM_NAME_CHOICES = (
        (FORM_268A, 'Form 268a'),
        (FORM_268B, 'Form 268b'),
    )

    BUSHFIRE_DISTRICT_ALIASES = {
        'PHS' : 'PH',
        'SWC' : 'SC',
        'EKM' : 'KIMB',
        'WKM' : 'KIMB',
        'KAL' : 'GF',
        'PIL' : 'PF',
    }


    fmt = "%Y-%m-%d %H:%M"

    prescription = models.ForeignKey(Prescription, verbose_name="Burn ID", related_name='prescribed_burn', null=True, blank=True)
#    prescription = ChainedForeignKey(
#        Prescription, chained_field="region", chained_model_field="region",
#        show_all=False, auto_choose=True, blank=True, null=True)

    fire_tenures = models.ManyToManyField(FireTenure, blank=True)

    # Required for Fire records
    fire_id = models.CharField(verbose_name="Fire Number", max_length=8, null=True, blank=True)
    fire_name = models.TextField(verbose_name="Name", null=True, blank=True)
    region = models.PositiveSmallIntegerField(choices=[(r.id, r.name) for r in Region.objects.all()], null=True, blank=True)
    district = ChainedForeignKey(
        District, chained_field="region", chained_model_field="region",
        show_all=False, auto_choose=True, blank=True, null=True)
    fire_tenures = models.ManyToManyField(FireTenure, verbose_name="Tenures", blank=True)
    date = models.DateField(auto_now_add=False)
    form_name = models.PositiveSmallIntegerField(verbose_name="Form Name (268a / 268b)", choices=FORM_NAME_CHOICES, editable=True)
    status = models.PositiveSmallIntegerField(verbose_name="Active", choices=BURN_CHOICES, null=True, blank=True)
    ignition_status = models.PositiveSmallIntegerField(verbose_name="Ignition Status", choices=IGNITION_STATUS_CHOICES, null=True, blank=True)
    external_assist = models.ManyToManyField(ExternalAssist, verbose_name="Assistance received from", blank=True)

    planned_area = models.DecimalField(
        verbose_name="Today's treatment area (ha)", max_digits=12, decimal_places=1,
        validators=[MinValueValidator(0.0)], null=True, blank=True)
    area = models.DecimalField(
        verbose_name="Area Burnt Yesterday (ha)", max_digits=12, decimal_places=1,
        validators=[MinValueValidator(0.0)], null=True, blank=True)

    planned_distance = models.DecimalField(
        verbose_name="Today's treatment distance (km)", max_digits=12, decimal_places=1,
        validators=[MinValueValidator(0.0)], null=True, blank=True)
    distance = models.DecimalField(
        verbose_name="Distance Burnt Yesterday (km)", max_digits=12, decimal_places=1,
        validators=[MinValueValidator(0.0)], null=True, blank=True)

    tenures= models.TextField(verbose_name="Tenure")
    location= models.TextField(verbose_name="Location", null=True, blank=True)
    est_start = models.TimeField('Estimated Start Time', null=True, blank=True)
    conditions = models.TextField(verbose_name='SDO Special Conditions', null=True, blank=True)
    rolled = models.BooleanField(verbose_name="Fire Rolled from yesterday", editable=False, default=False)

    def clean(self):
        if not self.form_name:
            if self.prescription and self.area==None and self.distance==None:
                self.form_name = 1
            else:
                self.form_name = 2

        if self.prescription and not (self.region and self.district):
            self.region = self.prescription.region.id
            self.district = self.prescription.district


    def clean_fire_id(self):
        if not (len(self.fire_id)>=6 and self.fire_id[-4]=='_'): # ignore if this is an edit (field is readonly)
            if not self.fire_id or str(self.fire_id)[0] in ('-', '+') or not str(self.fire_id).isdigit() or not len(self.fire_id)==3:
                raise ValidationError("You must enter numeric digit with 3 characters (001 - 999).")

            if int(self.fire_id)<1 or int(self.fire_id)>999:
                raise ValidationError("Value must be in range (001 - 999).")

            district = self.BUSHFIRE_DISTRICT_ALIASES[self.district.code] if self.BUSHFIRE_DISTRICT_ALIASES.has_key(self.district.code) else self.district.code
            fire_id = "%s_%s" % (district, self.fire_id)
            pb = PrescribedBurn.objects.filter(fire_id=fire_id, date=self.date)
            if pb and pb[0].id != self.id:
                raise ValidationError("{} already exists for date {}".format(fire_id, self.date))

            self.fire_id = fire_id

    def clean_date(self):
        today = date.today()
        tomorrow = today + timedelta(days=1)
        if not self.pk and (self.date < today or self.date > tomorrow):
            raise ValidationError("You must enter burn plans for today or tommorow's date only.")

    def clean_planned_distance(self):
        if self.planned_area==None and self.planned_distance==None:
            raise ValidationError("Must input at least one of Area or Distance")

    def clean_distance(self):
        if self.area==None and self.distance==None:
            raise ValidationError("Must input at least one of Area or Distance")

    @property
    def is_acknowledged(self):
        if all(x in [i.acknow_type for i in self.acknowledgements.all()] for x in ['SDO_A','SDO_B']):
            return True
        else:
            return False

    @property
    def user_a_record(self):
        ack = self.acknowledgements.filter(acknow_type='USER_A')
        return ack[0].record if ack else None

    @property
    def srm_a_record(self):
        ack = self.acknowledgements.filter(acknow_type='SRM_A')
        return ack[0].record if ack else None

    @property
    def sdo_a_record(self):
        ack = self.acknowledgements.filter(acknow_type='SDO_A')
        return ack[0].record if ack else None

    @property
    def user_b_record(self):
        ack = self.acknowledgements.filter(acknow_type='USER_B')
        return ack[0].record if ack else None

    @property
    def srm_b_record(self):
        ack = self.acknowledgements.filter(acknow_type='SRM_B')
        return ack[0].record if ack else None

    @property
    def sdo_b_record(self):
        ack = self.acknowledgements.filter(acknow_type='SDO_B')
        return ack[0].record if ack else None

    @property
    def formA_isDraft(self):
        return not any(x in [i.acknow_type for i in self.acknowledgements.all()] for x in ['USER_A', 'SRM_A', 'SDO_A'])

    @property
    def formB_isDraft(self):
        return not any(x in [i.acknow_type for i in self.acknowledgements.all()] for x in ['USER_B', 'SRM_B', 'SDO_B'])

    @property
    def formA_user_acknowledged(self):
        return True if self.user_a_record else False

    @property
    def formA_srm_acknowledged(self):
        return True if self.srm_a_record else False

    @property
    def formA_sdo_acknowledged(self):
        return True if self.sdo_a_record else False

    @property
    def formB_user_acknowledged(self):
        return True if self.user_b_record else False

    @property
    def formB_srm_acknowledged(self):
        return True if self.srm_b_record else False

    @property
    def formB_sdo_acknowledged(self):
        return True if self.sdo_b_record else False

    @property
    def fire_type(self):
        return "Burn" if self.prescription else "Fire"

    @property
    def fire_idd(self):
        if self.prescription:
            return self.prescription.burn_id
        else:
            return self.fire_id

    @property
    def further_ignitions_req(self):
        if self.ignition_status==self.IGNITION_STATUS_REQUIRED:
            return True
        elif self.ignition_status==self.IGNITION_STATUS_COMPLETED:
            return False
        return None


    @property
    def active(self):
        if self.status==self.BURN_ACTIVE:
            return True
        elif self.status==self.BURN_INACTIVE:
            return False
        return None

    @property
    def has_conditions(self):
        if self.conditions:
            return True
        return False

    @property
    def planned_area_str(self):
        _str = ''
        if self.planned_area:
            _str += str(self.planned_area) + " ha {} ".format('-' if self.planned_distance else '')

        if self.planned_distance:
            _str += str(self.planned_distance) + " km"

        return _str

    @property
    def area_str(self):
        _str = ''
        if self.area>=0:
            _str += str(self.area) + " ha {} ".format('-' if self.distance else '')

        if self.distance>=0:
            _str += str(self.distance) + " km"

        return _str

    @property
    def tenures_str(self):
        if self.prescription:
            return self.tenures #', '.join([t.name for t in self.tenures.all()])
        else:
            return ', '.join([i.name for i in self.fire_tenures.all()])

    @property
    def had_external_assist(self):
        if self.external_assist.all().count() > 0:
            return True
        return False

    @property
    def external_assist_str(self):
        return ', '.join([i.name for i in self.external_assist.all()])

    @property
    def name(self):
        if self.prescription:
            return self.prescription.name
        else:
            return self.fire_name

    @property
    def get_region(self):
        return self.prescription.region if self.prescription else self.region

    @property
    def get_district(self):
        return self.prescription.district if self.prescription else self.district

    @property
    def can_endorse(self):
        return (self.status == self.APPROVAL_SUBMITTED)

    @property
    def can_approve(self):
        return (self.status == self.APPROVAL_ENDORSED)

    @property
    def last_ignition(self):
        if self.prescription:
            area_achievements = self.prescription.areaachievement_set.all()
            if area_achievements:
                return max([i.ignition for i in area_achievements])
        return None

    def __str__(self):
        return self.prescription.burn_id if self.prescription else self.fire_id

    class Meta:
        unique_together = ('prescription', 'date', 'form_name', 'location')
        verbose_name = 'Prescribed Burn'
        verbose_name_plural = 'Prescribed Burns'
        permissions = (
            ("can_endorse", "Can endorse burns"),
            ("can_approve", "Can approve burns"),
        )


class AircraftApproval(models.Model):
    aircraft_burn = models.ForeignKey('AircraftBurn', related_name='approvals')
    user = models.ForeignKey(User, help_text="User", null=True, blank=True)
    approval_type = models.CharField(max_length=64, null=True, blank=True)
    approval_date = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    fmt = "%d/%m/%Y %H:%M"

    @property
    def record(self):
        username = '{} {}'.format(self.user.first_name[0], self.user.last_name)
        return "{} {}".format(
            username, self.approval_date.astimezone(tz.tzlocal()).strftime(self.fmt)
        )

    def remove(self):
        self.delete()

    def __str__(self):
        return "{} - {} - {}".format(
            self.aircraft_burn, self.approval_type, self.record)


@python_2_unicode_compatible
class AircraftBurn(Audit):
    APPROVAL_DRAFT = 'DRAFT'
    APPROVAL_SUBMITTED = 'USER'
    APPROVAL_ENDORSED = 'SRM'
    APPROVAL_APPROVED = 'SDO'
    APPROVAL_CHOICES = (
        (APPROVAL_DRAFT, 'Draft'),
        (APPROVAL_SUBMITTED, 'District Submitted'),
        (APPROVAL_ENDORSED, 'Region Endorsed'),
        (APPROVAL_APPROVED, 'State Approved'),
    )

    fmt = "%Y-%m-%d %H:%M"

    prescription = models.ForeignKey(Prescription, verbose_name="Burn ID", related_name='aircraft_burns', null=True, blank=True)
    #prescribed_burn = models.ForeignKey(PrescribedBurn, verbose_name="Daily Burn ID", related_name='aircraft_burn', null=True, blank=True)

    date = models.DateField(auto_now_add=False)
    area = models.DecimalField(
        verbose_name="Area (ha)", max_digits=12, decimal_places=1,
        validators=[MinValueValidator(0.0)], null=True, blank=True)
    est_start = models.TimeField('Estimated Start Time', null=True, blank=True)
    bombing_duration = models.DecimalField(
        verbose_name="Bombing Duration (hrs)", max_digits=5, decimal_places=1,
        validators=[MinValueValidator(0.0)], null=True, blank=True)
    min_smc = models.DecimalField(
        verbose_name="Min SMC", max_digits=5, decimal_places=1,
        validators=[MinValueValidator(0.0)], null=True, blank=True)
    max_fdi = models.DecimalField(
        verbose_name="Max FDI", max_digits=5, decimal_places=1,
        validators=[MinValueValidator(0.0)], null=True, blank=True)
    sdi_per_day = models.DecimalField(
        verbose_name="SDI Each Day", max_digits=5, decimal_places=1,
        validators=[MinValueValidator(0.0)], null=True, blank=True)
    flight_seq= models.TextField(verbose_name="Flight Sequence", null=True, blank=True)
    aircraft_rego= models.TextField(verbose_name="Aircraft Rego", null=True, blank=True)
    arrival_time= models.TimeField(verbose_name="Arrival Time Over Burn", null=True, blank=True)
    program= models.TextField(verbose_name="Program", null=True, blank=True)
    aircrew= models.TextField(verbose_name="Aircrew", null=True, blank=True)

    rolled = models.BooleanField(verbose_name="Fire Rolled from yesterday", editable=False, default=False)

    @property
    def regional_approval(self):
        return True

    @property
    def state_duty_approval(self):
        return True

    @property
    def state_aviation_approval(self):
        return True

    def __str__(self):
        return self.prescription.burn_id

    class Meta:
        unique_together = ('prescription', 'date')
        verbose_name = 'Aircraft Burn'
        verbose_name_plural = 'Aircraft Burns'
        permissions = (
            ("can_endorse", "Can endorse burns"),
            ("can_approve", "Can approve burns"),
        )


