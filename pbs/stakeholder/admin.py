from pbs.admin import BaseAdmin
from pbs.prescription.admin import PrescriptionMixin, SavePrescriptionMixin


class CriticalStakeholderAdmin(PrescriptionMixin, SavePrescriptionMixin,
                               BaseAdmin):
    list_display = ('name', 'organisation', 'interest')
    list_editable = ('name', 'organisation', 'interest')
    list_empty_form = True
    list_display_links = (None,)
    actions = None
    can_delete = True
    lock_after = "endorsement"


class PublicContactAdmin(PrescriptionMixin, SavePrescriptionMixin,
                         BaseAdmin):
    list_display = ('name', 'organisation', 'person', 'comments')
    list_editable = ('name', 'organisation', 'person', 'comments')
    list_empty_form = True
    list_display_links = (None,)
    actions = None
    can_delete = True
    lock_after = "never"

    def get_readonly_fields(self, request, obj=None):
        """
        Overriding the equiv. method in PrescriptionMixin to allow the fields
        here to be editable at any stage of prescription completion
        """
        return super(PrescriptionMixin, self).get_readonly_fields(request, obj)


class NotificationAdmin(PrescriptionMixin, SavePrescriptionMixin, BaseAdmin):
    list_display = ('notified', 'contacted', 'organisation', 'address',
                    'phone')
    list_editable = ('notified', 'contacted', 'organisation', 'address',
                     'phone')
    list_empty_form = True
    list_display_links = (None,)
    actions = None
    can_delete = True
    lock_after = "never"

    def get_readonly_fields(self, request, obj=None):
        """
        Overriding the equiv. method in PrescriptionMixin to allow the fields
        here to be editable at any stage of prescription completion
        """
        return super(PrescriptionMixin, self).get_readonly_fields(request, obj)
