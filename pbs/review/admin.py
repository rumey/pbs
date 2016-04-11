from datetime import date
from pbs.admin import BaseAdmin
from swingers.admin import DetailAdmin
from functools import update_wrapper
from django.contrib.auth.models import Group
from django.template.response import TemplateResponse

from pbs.review.models import BurnState, PlannedBurn, OngoingBurn
from pbs.review.forms import BurnStateSummaryForm, PlannedBurnSummaryForm
from pbs.prescription.models import Prescription, Approval
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
        # Queryset business rules:
        # * Prescription approved, open, ignition not started or started.
        # * Approval ``valid_to`` date is not in the past.
        presc_ids = [a.prescription.pk for a in Approval.objects.filter(valid_to__gte=date.today())]
        queryset = Prescription.objects.filter(
            approval_status=Prescription.APPROVAL_APPROVED,
            status=Prescription.STATUS_OPEN,
            ignition_status__in=[Prescription.IGNITION_NOT_STARTED, Prescription.IGNITION_COMMENCED],
            pk__in=presc_ids
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


#class PlannedBurnAdmin(DetailAdmin, BaseAdmin):
#    """
#    The (current) Day's Planned Burns (Fire 268a)
#    """
#    #epfp_planned_burn_template = 'admin/review/epfp_planned_burn.html'
#    epfp_planned_burn_template = 'admin/epfp_daily_burn_program.html'
#
#    def get_urls(self):
#        """
#        Add a view to clear the current prescription from the session
#        """
#        from django.conf.urls import patterns, url
#
#        def wrap(view):
#            def wrapper(*args, **kwargs):
#                return self.admin_site.admin_view(view)(*args, **kwargs)
#            return update_wrapper(wrapper, view)
#
#        urlpatterns = patterns(
#            '',
#            url(r'^plannedburn/$',
#                wrap(self.epfp_planned_burn),
#                name='epfp_planned_burn'),
#        )
#
#        return urlpatterns + super(PlannedBurnAdmin, self).get_urls()
#
#    def epfp_planned_burn(self, request, extra_context=None):
#        """
#        Display a list of the current day's planned burns
#        """
#        report_set = {'epfp_planned_burns'}
#        report = request.GET.get('report', 'epfp_planned_burns')
#        if report not in report_set:
#            report = 'epfp_planned_burns'
#
#        title = "Today's Planned Burn Program"
#
#        # Use the region from the request.
#        if request.REQUEST.has_key('date'):
#            dt = request.REQUEST.get('date', None)
#            if dt:
#                dt = datetime.strptime(dt, '%Y-%m-%d')
#        else:
#            dt = date.today()
#        queryset = PlannedBurn.objects.filter(date__gte=dt)
#
#        if request.REQUEST.has_key('region'):
#            region = request.REQUEST.get('region', None)
#            if region:
#                queryset = queryset.filter(prescription__region=region)
#
#        if request.REQUEST.has_key('report'):
#            report = request.REQUEST.get('report', None)
#
#        context = {
#            'title': title,
#            'queryset': queryset.order_by('prescription__burn_id'),
#            'form': PlannedBurnSummaryForm(request.GET),
#            'report': report,
#            'username': request.user.username,
#            'date': dt.strftime('%Y-%m-%d')
#        }
#        context.update(extra_context or {})
#        return TemplateResponse(request, self.epfp_planned_burn_template, context)
#
##    def endorse_authorise_summary(self, request, extra_context=None):
##        """
##        Display summaries of prescriptions, approvals and ignitions.
##
##        DEV:
##
##        """
##        form = EndorseAuthoriseSummaryForm(request.GET)
##
##        report_set = {'summary', 'approvals', 'ignitions'}
##        report = request.GET.get('report', 'summary')
##        if report not in report_set:
##            report = 'summary'
##
##        export_csv = True if request.GET.get('Export_CSV') == 'export_csv' else False
##
##        if request.GET.get('fromDate'):
##            fromDate = request.GET.get('fromDate')
##            fromDate = datetime.datetime.strptime(fromDate, '%d-%m-%Y').date()
##        else:
##            # default - beginning of financial year
##            yr = datetime.date.today().year
##            fromDate = datetime.date(yr, 7, 1)
##
##        if request.GET.get('toDate'):
##            toDate = request.GET.get('toDate')
##            toDate = datetime.datetime.strptime(toDate, '%d-%m-%Y').date()
##        else:
##            toDate = datetime.date.today()
##
##        burns = []
##        if report == 'summary':
##            title = _("Endorsements summary")
##            queryset = Prescription.objects.filter(
##                endorsement_status=Prescription.ENDORSEMENT_SUBMITTED)
##        elif report == 'approvals':
##            title = _("Approvals summary")
##            queryset = Prescription.objects.filter(
##                approval_status=Prescription.APPROVAL_SUBMITTED)
##        elif report == 'ignitions':
##            title = _("Ignitions summary")
##            queryset = None
##            burns = self.get_burns(fromDate, toDate)
##        else:
##            raise ValueError("Report {} must be in {}".format(report, report_set))
##
##        if export_csv:
##            return self.export_to_csv(request, fromDate, toDate, burns)
##        if queryset:
##            queryset.prefetch_related('endorsing_roles')
##
##        if form.is_valid():
##            region = form.cleaned_data.get('region', None)
##            district = form.cleaned_data.get('district', None)
##
##            if region:
##                queryset = queryset.filter(region=region)
##
##            if district:
##                queryset = queryset.filter(district=district)
##
##        context = {
##            'title': title,
##            'prescriptions': queryset,
##            'form': form,
##            'report': report,
##            'burns': burns,
##            'fromDate': fromDate,
##            'toDate': toDate,
##        }
##        context.update(extra_context or {})
##        return TemplateResponse(request, "admin/endorse_authorise_summary.html", context,
##                                current_app=self.name)
#
#
#class OngoingBurnAdmin(DetailAdmin, BaseAdmin):
#    """
#    The Current Ongoing Burns (Fire 268b)
#    """
#    epfp_ongoing_burn_template = 'admin/review/epfp_ongoing_burn.html'
#
#    def get_urls(self):
#        """
#        Add a view to clear the current prescription from the session
#        """
#        from django.conf.urls import patterns, url
#
#        def wrap(view):
#            def wrapper(*args, **kwargs):
#                return self.admin_site.admin_view(view)(*args, **kwargs)
#            return update_wrapper(wrapper, view)
#
#        urlpatterns = patterns(
#            '',
#            url(r'^epfp-ongoing/$',
#                wrap(self.epfp_ongoing_burn),
#                name='epfp_ongoing_burn'),
#        )
#
#        return urlpatterns + super(OngoingBurnAdmin, self).get_urls()
#
#    def epfp_ongoing_burn(self, request, extra_context=None):
#        """
#        Display a list of the current ongoing burns
#        """
#        report_set = {'epfp_ongoing_burns'}
#        report = request.GET.get('report', 'epfp_ongoing_burns')
#        if report not in report_set:
#            report = 'epfp_ongoing_burns'
#
#        title = "Summary of Current Fire Load"
#
#        # Use the region from the request.
#        if request.REQUEST.has_key('date'):
#            dt = request.REQUEST.get('date', None)
#            if dt:
#                dt = datetime.strptime(dt, '%Y-%m-%d')
#        else:
#            dt = date.today()
#        queryset = PlannedBurn.objects.filter(date__gte=dt)
#
#        if request.REQUEST.has_key('region'):
#            region = request.REQUEST.get('region', None)
#            if region:
#                queryset = queryset.filter(prescription__region=region)
#
#        context = {
#            'title': title,
#            'queryset': queryset.order_by('prescription__burn_id'),
#            'form': PlannedBurnSummaryForm(request.GET),
#            'report': report,
#            'username': request.user.username,
#            'date': dt.strftime('%Y-%m-%d')
#        }
#        context.update(extra_context or {})
#        return TemplateResponse(request, self.epfp_ongoing_burn_template, context)
#
#
