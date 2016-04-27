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


#@python_2_unicode_compatible
#class ApprovingRole(models.Model):
#    name = models.CharField(max_length=320)
#
#    def __str__(self):
#        return self.name
#
#    class Meta:
#        ordering = ['name']


@python_2_unicode_compatible
class ExternalAssist(models.Model):
    name = models.CharField(max_length=12)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Fire(Audit):
    FIRE_ACTIVE = 1
    FIRE_INACTIVE = 2

    APPROVAL_DRAFT = 1
    APPROVAL_SUBMITTED = 2
    APPROVAL_ENDORSED = 3
    APPROVAL_APPROVED = 4
    APPROVAL_CHOICES = (
        (APPROVAL_DRAFT, 'Draft'),
        (APPROVAL_SUBMITTED, 'Submitted'),
        (APPROVAL_ENDORSED, 'Endorsed'),
        (APPROVAL_APPROVED, 'Approved'),
    )

    fire_id = models.CharField(verbose_name="Fire ID?", max_length=10, null=True, blank=True)
    name = models.TextField(verbose_name="Fire Description/Details?", null=True, blank=True)
    region = models.PositiveSmallIntegerField(verbose_name="Fire Region", choices=[(r.id, r.name) for r in Region.objects.all()], null=True, blank=True)
    district = ChainedForeignKey(
        District, chained_field="region", chained_model_field="region",
        show_all=False, auto_choose=True, blank=True, null=True)

    #user = models.ForeignKey(User, help_text="User")
    date = models.DateField(auto_now_add=False)
    active = models.NullBooleanField(verbose_name="Fire Active?", null=True, blank=True)
    #external_assist = models.BooleanField(verbose_name="External Assistance?", blank=True)
    external_assist = models.ManyToManyField(ExternalAssist, blank=True)
    area = models.DecimalField(
        verbose_name="Planned Fire Area (ha)", max_digits=12, decimal_places=1,
        validators=[MinValueValidator(0)], null=True, blank=True)
        #validators=[MinValueValidator(0)], default=0.0)
    tenures = models.ManyToManyField(Tenure, blank=True)
    location= models.TextField(verbose_name="Location", null=True, blank=True)

    submitted_by = models.ForeignKey(User, verbose_name="Submitting User", blank=True, null=True, related_name='fire_submitted_by')
    endorsed_by = models.ForeignKey(User, verbose_name="Endorsing Officer", blank=True, null=True, related_name='fire_endorsed_by')
    approved_by = models.ForeignKey(User, verbose_name="Approving Officer", blank=True, null=True, related_name='fire_approved_by')

    approval_status = models.PositiveSmallIntegerField(
        verbose_name="Approval Status", choices=APPROVAL_CHOICES,
        default=APPROVAL_DRAFT)
    approval_status_modified = models.DateTimeField(
        verbose_name="Approval Status Modified", editable=False, null=True)


    @property
    def tenures_str(self):
        return ', '.join([t.name for t in self.tenures.all()])

    @property
    def had_external_assist(self):
        if self.external_assist.all().count() > 0:
            return True
        return False

    @property
    def external_assist_str(self):
        return ', '.join([i.name for i in self.external_assist.all()])

    @property
    def status(self):
        if self.active:
            return self.FIRE_ACTIVE
        return self.FIRE_INACTIVE

#    def save(self, **kwargs):
#        super(Fire, self).save(**kwargs)
#        tenures = ', '.join([t.name for t in self.prescription.tenures.all()])
#        if not self.location:
#            self.location = self.prescription.location
#        if not self.tenures and tenures:
#            self.tenures = tenures
#        super(PrescribedBurn, self).save()

    @property
    def can_endorse(self):
        """
        Return true if this fire can be submitted for endorsement.
        """
        return (self.status == self.APPROVAL_SUBMITTED)

    @property
    def can_approve(self):
        """
        Return true if this fire can be submitted for Approval.
        """
        return (self.status == self.APPROVAL_ENDORSED)

    def __str__(self):
        return self.fire_id

    class Meta:
        unique_together = ('fire_id', 'date',)
        verbose_name = 'Fire'
        verbose_name_plural = 'Fires'
        permissions = (
            ("can_endorse", "Can endorse fire actions"),
            ("can_approve", "Can approve fire actions"),
        )

class PrescribedBurn(Audit):
    BURN_PLANNED = 0
    BURN_ACTIVE = 1
    BURN_INACTIVE = 2
    BURN_COMPLETED = 3
    BURN_CHOICES = (
        (BURN_PLANNED, 'Planned'),
        (BURN_ACTIVE, 'Active'),
        (BURN_INACTIVE, 'Inactive'),
        (BURN_COMPLETED, 'Completed')
    )

    APPROVAL_DRAFT = 1
    APPROVAL_SUBMITTED = 2
    APPROVAL_ENDORSED = 3
    APPROVAL_APPROVED = 4
    APPROVAL_CHOICES = (
        (APPROVAL_DRAFT, 'Draft'),
        (APPROVAL_SUBMITTED, 'Submitted'),
        (APPROVAL_ENDORSED, 'Endorsed'),
        (APPROVAL_APPROVED, 'Approved'),
    )

    prescription = models.ForeignKey(Prescription, related_name='prescribed_burn', null=True, blank=True)
    #user = models.ForeignKey(User, help_text="User")
    date = models.DateField(auto_now_add=False)

    status = models.PositiveSmallIntegerField(verbose_name="Burn Status", choices=BURN_CHOICES, null=True, blank=True)
#    active = models.NullBooleanField(verbose_name="Burn Active?", null=True, blank=True)

    further_ignitions = models.BooleanField(verbose_name="Further ignitions required?")
#    external_assist = models.BooleanField(verbose_name="External Assistance?", blank=True)
    external_assist = models.ManyToManyField(ExternalAssist, blank=True)
    area = models.DecimalField(
        verbose_name="Area Achieved Yesterday (ha)", max_digits=12, decimal_places=1,
        validators=[MinValueValidator(0.1)], null=True, blank=True)
    tenures= models.TextField(verbose_name="Tenure")
    location= models.TextField(verbose_name="Location", null=True, blank=True)

    est_start = models.TimeField('Estimated Start Time')
    conditions = models.TextField(verbose_name='Special Conditions', null=True, blank=True)

    submitted_by = models.ForeignKey(User, verbose_name="Submitting User", blank=True, null=True, related_name='burn_submitted_by')
    endorsed_by = models.ForeignKey(User, verbose_name="Endorsing Officer", blank=True, null=True, related_name='burn_endorsed_by')
    approved_by = models.ForeignKey(User, verbose_name="Approving Officer", blank=True, null=True, related_name='burn_approved_by')

    approval_status = models.PositiveSmallIntegerField(
        verbose_name="Approval Status", choices=APPROVAL_CHOICES,
        default=APPROVAL_DRAFT)
    approval_status_modified = models.DateTimeField(
        verbose_name="Approval Status Modified", editable=False, null=True)

    def clean_date(self):
        today = date.today()
        tomorrow = today + timedelta(days=1)
        if self.date < today or self.date > tomorrow:
            raise ValidationError("You must enter burn plans for today or tommorow's date only.")

    def clean_sdo_approve(self):
        """
        Check that status 'Active' and 'Area burnt yesterday' are not Null.
        Cannot approve if data is missing from 268b records
        """
        #TODO - 1254
        pass

    @property
    def fire_id(self):
        return self.prescription.burn_id

    @property
    def active(self):
        if self.status==self.BURN_ACTIVE:
            return True
        elif self.status==self.BURN_INACTIVE:
            return False
        return None

    @property
    def completed(self):
        if self.status==self.BURN_COMPLETED:
            return True
        return False

    @property
    def has_conditions(self):
        if self.conditions:
            return True
        return False

    @property
    def tenures_str(self):
        return self.tenures #', '.join([t.name for t in self.tenures.all()])

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
        return self.prescription.name

    @property
    def region(self):
        return self.prescription.region

    @property
    def district(self):
        return self.prescription.district

    @property
    def can_endorse(self):
        """
        Return true if this fire can be submitted for endorsement.
        """
        return (self.status == self.APPROVAL_SUBMITTED)

    @property
    def can_approve(self):
        """
        Return true if this fire can be submitted for Approval.
        """
        return (self.status == self.APPROVAL_ENDORSED)

    def save(self, **kwargs):
        super(PrescribedBurn, self).save(**kwargs)
        tenures = self.tenures_str
        if not self.location:
            self.location = self.prescription.location
        if not self.tenures and tenures:
            self.tenures = tenures
        super(PrescribedBurn, self).save()

    def __str__(self):
        return self.prescription.burn_id

    class Meta:
        unique_together = ('prescription', 'date',)
        verbose_name = 'Prescribed Burn'
        verbose_name_plural = 'Prescribed Burns'
        permissions = (
            ("can_endorse", "Can endorse burns"),
            ("can_approve", "Can approve burns"),
        )




