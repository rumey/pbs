from django.db import models
from datetime import datetime
from django.contrib.auth.models import User
from pbs.prescription.models import (Prescription)
from dateutil import tz

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

