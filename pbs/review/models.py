from django.db import models
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from pbs.prescription.models import (Prescription)
from dateutil import tz

from django.core.validators import MaxValueValidator, MinValueValidator


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


class PlannedBurn(models.Model):
    prescription = models.ForeignKey(Prescription, related_name='planned_burn')
    user = models.ForeignKey(User, help_text="User")
    date = models.DateField(auto_now_add=True)
    area = models.DecimalField(
        verbose_name="Planned Burn Area (ha)", max_digits=7, decimal_places=1,
        help_text="Planned burn area (in ha)",
        validators=[MinValueValidator(0)], default=0.0
    )
    est_start = models.TimeField('Estimated Start Time')
    has_contigency = models.BooleanField(verbose_name="Contingency plan in place?", blank=True)
    has_monitoring = models.BooleanField(verbose_name="Monitoring plan in place?", blank=True)
    invite = models.CharField(verbose_name="Invite to Assist?", max_length=24, null=True, blank=True)
    conditions = models.TextField(verbose_name='Special Conditions', null=True, blank=True)
    #review_type = models.CharField(max_length=64)

    def contains_lga(self):
        return 'LGA' in self.invite

    def contains_dfes(self):
        return 'DFES' in self.invite

class OngoingBurn(models.Model):
    IGNTYPE_BURN = 1
    IGNTYPE_FIRE = 2
    IGNTYPE_CHOICES = (
        (IGNTYPE_BURN, 'BURN'),
        (IGNTYPE_FIRE, 'FIRE'),
    )

    prescription = models.ForeignKey(Prescription, related_name='ongoing_burn', null=True, blank=True)
    fire_id = models.CharField(verbose_name="Fire ID?", max_length=10, null=True, blank=True)
    fire_desc = models.TextField(verbose_name="Fire Description/Details?", null=True, blank=True)
    user = models.ForeignKey(User, help_text="User")
    date = models.DateField(auto_now_add=True)
    ignition_type = models.PositiveSmallIntegerField(
        verbose_name="Ignition Type (Burn/Fire)", choices=IGNTYPE_CHOICES)

    burn_active = models.BooleanField(verbose_name="Burn Active?", blank=True)
    further_ignitions = models.BooleanField(verbose_name="Further ignitions required?", blank=True)
    ignition_completed = models.BooleanField(verbose_name="Ignition now completed?", blank=True)
    #tenure = models.CharField(verbose_name="Tenure", max_length=24, null=True, blank=True)
    external_assist = models.BooleanField(verbose_name="External Assistance?", blank=True)

    def ignition_id(self):
        if self.ignition_type==1:
            return self.prescription.burn_id
        else:
            return self.fire_id

    def ignition_desc(self):
        if self.ignition_type==1:
            return self.prescription.name
        else:
            return self.fire_desc

    def area(self):
        if self.ignition_type==1:
            yesterday = self.date - timedelta(days=1)
            pb = PlannedBurn.objects.filter(prescription__id=self.prescription.id, date=yesterday)
            if pb:
                return pb[0].area

        return None

    def tenures(self):
        if self.ignition_type==1:
            return [t.name for t in self.prescription.tenures.all()]
        return None

#    def external_assist(self):
#        pb = PlannedBurn.objects.filter(prescription__id=self.prescription.id, date=yesterday)
#        if pb.invite:
#            return True
#        return False

class ActiveBurn(models.Model):
    prescription = models.ForeignKey(Prescription, related_name='active_burn')
