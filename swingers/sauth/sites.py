from django.db.models.base import ModelBase
from django.contrib import admin

from swingers.models import Audit
from swingers.sauth.admin import AuditAdmin


class AuditSite(admin.AdminSite):
    def register(self, model_or_iterable, admin_class=None, **options):
        if isinstance(model_or_iterable, ModelBase):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if issubclass(model, Audit):
                if not admin_class:
                    admin_class = AuditAdmin

            super(AuditSite, self).register(model, admin_class, **options)
