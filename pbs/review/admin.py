from pbs.admin import BaseAdmin
from swingers.admin import DetailAdmin
from functools import update_wrapper
from django.contrib.auth.models import Group
from django.template.response import TemplateResponse

from pbs.review.models import BurnState
from pbs.review.forms import BurnStateSummaryForm
from pbs.prescription.models import Prescription
from datetime import datetime
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse


class BurnStateAdmin(DetailAdmin, BaseAdmin):
    """
    SDO Burn State Report
    """
    epfp_review_template = 'admin/review/epfp_review_summary.html'

    fmsb_group = Group.objects.get(name='Fire Management Services Branch')
    drfms_group = Group.objects.get(name='Director Fire and Regional Services')

    def get_urls(self):
        """
        Add a view to clear the current prescription from the session
        """
        from django.conf.urls import patterns, url

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        urlpatterns = patterns(
            '',
            url(r'^epfp-review/$',
                wrap(self.epfp_review_summary),
                name='epfp_review_summary'),
        )

        return urlpatterns + super(BurnStateAdmin, self).get_urls()

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """
        Redirect to main review page on change.

        This is done via 'auth.group'  permissions
        ["view_burnstate", "review", "burnstate"] --> auto provides url --> review/burnstate/(\d+)/change
        """
        # the below logic assumes, USER can be part of FMSB or DRFMS - not both
        if self.fmsb_group in request.user.groups.all():
            p = Prescription.objects.get(id=object_id)
            s, created = BurnState.objects.get_or_create(prescription=p, user=request.user, review_type='FMSB')
        elif self.drfms_group in request.user.groups.all():
            p = Prescription.objects.get(id=object_id)
            s, created = BurnState.objects.get_or_create(prescription=p, user=request.user, review_type='DRFMS')

        # if state already exists, update review_date
        if not created:
            s.review_date = datetime.now()
            s.save()

        url = reverse('admin:epfp_review_summary')
        return HttpResponseRedirect(url)

    def delete_view(self, request, object_id, extra_context=None):
        """
        Redirect to main review page on delete.

        This is done via 'auth.group'  permissions
        ["delete_burnstate", "review", "burnstate"] --> auto provides url --> review/burnstate/(\d+)/delete
        """
        response = super(BurnStateAdmin, self).delete_view(request, object_id, extra_context)

        if isinstance(response, HttpResponseRedirect):
            url = reverse('admin:epfp_review_summary')
            return HttpResponseRedirect(url)
        return response

    def epfp_review_summary(self, request, extra_context=None):
        """
        Display summaries of prescriptions, approvals and ignitions.
        """

        report_set = {'epfp_review'}
        report = request.GET.get('report', 'epfp_review')
        if report not in report_set:
            report = 'epfp_review'


        title = 'Day of burn ePFP review and confirmation (approved burns)'
        queryset = Prescription.objects.filter(
            approval_status=Prescription.APPROVAL_APPROVED,
            status=Prescription.STATUS_OPEN,
            ignition_status__in=[Prescription.IGNITION_NOT_STARTED, Prescription.IGNITION_COMMENCED],
        ).order_by('burn_id')

        # Use the region from the request.
        if request.REQUEST.has_key('region'):
            region = request.REQUEST.get('region', None)
        else:
            region = None
        # If no region in the request, use the user's profile.
        if not region and request.user.profile.region:
            region = request.user.profile.region
        # Finally, filter the queryset.
        if region:
            queryset = queryset.filter(region=region)

        context = {
            'title': title,
            'prescriptions': queryset,
            'form': BurnStateSummaryForm(request.GET),
            'report': report,
            'fms_state': None,
            'user_fmsb_group': self.fmsb_group in request.user.groups.all(),
            'user_drfms_group': self.drfms_group in request.user.groups.all(),
            'username': request.user.username,
        }
        context.update(extra_context or {})
        return TemplateResponse(request, self.epfp_review_template, context)
