from pbs.admin import BaseAdmin
from swingers.admin import DetailAdmin
from functools import update_wrapper
from django.contrib.auth.models import Group
from django.template.response import TemplateResponse

from pbs.review.models import BurnState, PrescribedBurn, Fire
from pbs.review.forms import BurnStateSummaryForm, PrescribedBurnForm, FireLoadForm
from pbs.prescription.models import Prescription, Approval
from datetime import datetime, date, timedelta
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
import itertools
from django.contrib.admin.util import quote, unquote, flatten_fieldsets
from django.conf import settings
from pbs.admin import BaseAdmin
from pbs.prescription.admin import PrescriptionMixin


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


class PrescribedBurnAdmin(DetailAdmin, BaseAdmin):
    fields = ("prescription", "date", "status", "further_ignitions", "external_assist", "area", "tenures", "location", "est_start", "invite", "conditions")
    #form = PlannedBurnForm

    def save_model(self, request, obj, form, change=True):
        """ Form does not assign user, do it here """
        obj.user = request.user
        obj.save()

    def response_post_save_change(self, request, obj):
        """
        Override the redirect url after successful save of an existing
        ContingencyAction.
        """
        url = reverse('admin:fireload_view')
        return HttpResponseRedirect(url)


    def get_urls(self):
        """
        Add an extra view to handle marking a treatment as complete.
        """
        from django.conf.urls import patterns, url

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.module_name

        urlpatterns = patterns(
            '',
            url(r'^add/burn/(\d+)/$',
                wrap(self.add_view),
                name='%s_%s_add' % info),
            url(r'^daily-burn-program/$',
                wrap(self.daily_burn_program),
                name='daily_burn_program'),

        )
        return urlpatterns + super(PrescribedBurnAdmin, self).get_urls()


    def daily_burn_program(self, request, extra_context=None):
        """
        Display a list of the current day's planned burns
        """
        report_set = {'epfp_planned', 'epfp_fireload', 'epfp_summary'}
        report = request.GET.get('report', 'epfp_planned')
        if report not in report_set:
            report = 'epfp_planned'

        if request.REQUEST.has_key('report'):
            report = request.REQUEST.get('report', None)


        # Use the region from the request.


        if request.REQUEST.has_key('date'):
            dt = request.REQUEST.get('date', None)
            if dt:
                dt = datetime.strptime(dt, '%Y-%m-%d')
#        elif request.REQUEST.has_key('tab_date'):
#            dt = request.REQUEST.get('tab_date', None)
#            if dt:
#                dt = datetime.datetime.strptime(dt, '%Y-%m-%d')
        else:
            dt = date.today()
            time_now = datetime.now().time()
            if time_now.hour > settings.DAY_ROLLOVER_HOUR:
                dt = dt + timedelta(days=1)


#        queryset= None
        #import ipdb; ipdb.set_trace()
        #qs_planned = PlannedBurn.objects.filter(date=dt)
        qs_burn = PrescribedBurn.objects.filter(date=dt)
        qs_fire = Fire.objects.filter(date=dt)
        #qs_fireload = FireLoad.objects.filter(prescription__date=dt, fire__date=dt)
        if report=='epfp_planned':
            title = "Today's Planned Burn Program"
            qs_burn = qs_burn.filter(status=PrescribedBurn.BURN_PLANNED)
            form = PrescribedBurnForm(request.GET)
#            pb = PrescribedBurn(user=request.user)
            #form = PlannedBurnForm(initial={'user': request.user})
            #form = PlannedBurnForm(request.POST or None, request=request)
#            if form.is_valid():
#                pb.save()
        elif report=='epfp_fireload':
            title = "Summary of Current Fire Load"
            form = FireLoadForm(request.GET)
        elif report=='epfp_summary':
            title = "Summary of Current and Planned Fires"
            qs_burn = qs_burn.filter(status__in=[PrescribedBurn.BURN_PLANNED, PrescribedBurn.BURN_ACTIVE])
            qs_fire = qs_fire.filter(active=True)
            #qs_fire = qs_fireload.filter(prescription__active=True, fire__active=True)
            #qs_fireload = qs_fireload.filter(prescription__active=True, fire__active=True)
            form = FireLoadForm(request.GET)
            #queryset = ActiveBurn.objects.filter(date__gte=dt)

        fire_type = 0
        if request.REQUEST.has_key('fire_type'):
            fire_type = int (request.REQUEST.get('fire_type', None))
#            if fire_type == 1:
#                qs_burn = qs_burn.filter(active=True)
#            elif fire_type == 2:
#                qs_fire = qs_fire.filter(active=True)
#

        #import ipdb; ipdb.set_trace()
        if request.REQUEST.has_key('region'):
            region = request.REQUEST.get('region', None)
            if region:
                if report=='epfp_planned':
                    qs_burn = qs_burn.filter(prescription__region=region)
                else:
                    qs_burn = qs_burn.filter(prescription__region=region)
                    qs_fire = qs_fire.filter(region=region)

        if request.REQUEST.has_key('district'):
            district = request.REQUEST.get('district', None)
            if district:
                if report=='epfp_planned':
                    qs_burn = qs_burn.filter(prescription__district=district)
                else:
                    qs_burn = qs_burn.filter(prescription__district=district)
                    qs_fire = qs_fire.filter(district=district)

        def qs_fireload(qs_burn, qs_fire, fire_type):
            if fire_type == 1:
                return qs_burn
            elif fire_type == 2:
                return qs_fire
            return list(itertools.chain(qs_burn, qs_fire))

        context = {
            'title': title,
            'qs_burn': qs_burn.order_by('prescription__burn_id') if qs_burn else [],
            'qs_fireload': qs_fireload(qs_burn, qs_fire, fire_type),
            'form': form,
            'report': report,
            'username': request.user.username,
            'date': dt.strftime('%Y-%m-%d'),
            'fire_type': fire_type,

            'active_burns_statewide': PrescribedBurn.objects.filter(status=PrescribedBurn.BURN_ACTIVE, date=dt).count(),
            'active_burns_non_statewide': PrescribedBurn.objects.filter(status=PrescribedBurn.BURN_ACTIVE, date=dt, prescription__region__in=[6, 7, 8]).count(),
            'active_fires_statewide': Fire.objects.filter(active=True, date=dt).count(),
            'active_fires_non_statewide': Fire.objects.filter(active=True, date=dt, region__in=[6, 7, 8]).count(),

        }
        context.update(extra_context or {})
        return TemplateResponse(request, "admin/epfp_daily_burn_program.html", context)

    def copy_prior_records(self, date):
        """
        Copy today's 'active' records to tomorrow
        To be run via Cron
        """

        time_now = datetime.datetime.now().time()
        today = datetime.date.today()
        tomorrow = date + datetime.timedelta(days=1)
        # copy permitted only after given time, and only for today to tomorrow
        if date != today:
            log.warn('WARNING: Cannot copy for date {}. Can only copy planned burn records from (current day) {} to tomorrow {}'.format(date, today, tomorrow))
            return

        if time_now.hour < settings.DAY_ROLLOVER_HOUR and date != today:
            log.warn('WARNING: cannot copy planned burn records to tomorrow, until after {} {}:00:00'.format(today.isoformat(), hour))
            return

        #only copy for today or tomorrow, and only copy if records for today/tomorrow don't already exist
#        if date!=today or date!=tomorrow or (PrescribedBurn.objects.filter(active=True, date=date).count()>0 or Fire.objects.filter(active=True, date=date).count()>0):
#            return

        qs_active_fireload = PrescribedBurn.objects.filter(active=True, date=today)
        qs_active_planned = Planned.objects.filter(active=True, date=today)

        for i in qs_active_planned:
            try:
                i.pk = None
                i.date = tomorrow
                i.area=None
                i.active=None
                i.save()
            except:
                # records already exist - pk (pres, date) will not allow overwrite, so ignore the exception
                pass


class FireAdmin(DetailAdmin, BaseAdmin):
    fields = ("fire_id", "name", "region", "district", "date", "active", "external_assist", "area", "tenures", "location")

#    def add_view(self, request, form_url='', extra_context=None):
#        model = self.model
#        import ipdb; ipdb.set_trace()
#        context = {
##            "user": request.user,
#        }
#        #form = PlannedBurnForm(initial={'user': request.user})
#        context.update(extra_context or {})
#        return super(FireAdmin, self).add_view(request, form_url, context)

    def _change_view(self, request, object_id, form_url='', extra_context=None):
        """
        Redirect to main review page on change.

        This is done via 'auth.group'  permissions
        ["view_fire", "review", "fire"] --> auto provides url --> review/fire/(\d+)/change
        """
        response = super(FireAdmin, self).change_view(request, object_id, form_url, extra_context)
        # the below logic assumes, USER can be part of FMSB or DRFMS - not both
        url = reverse('admin:fireload_view')
        return HttpResponseRedirect(url)

    def response_post_save_change(self, request, obj):
        """
        Override the redirect url after successful save of an existing
        ContingencyAction.
        """
        url = reverse('admin:fireload_view')
        return HttpResponseRedirect(url)

    def delete_view(self, request, object_id, extra_context=None):
        """
        Redirect to main review page on delete.

        This is done via 'auth.group'  permissions
        ["delete_fire", "review", "fire"] --> auto provides url --> review/fire/(\d+)/delete
        """
        response = super(FireAdmin, self).delete_view(request, object_id, extra_context)

        if isinstance(response, HttpResponseRedirect):
            url = reverse('admin:fireload_view')
            return HttpResponseRedirect(url)
        return response

    def save_model(self, request, obj, form, change=True):
        """ Form does not assign user, do it here """
        obj.user = request.user
        obj.save()


    def get_urls(self):
        """
        Add an extra view to handle marking a treatment as complete.
        """
        from django.conf.urls import patterns, url

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.module_name

        urlpatterns = patterns(
            '',
#            url(r'^add/fire/(\d+)/$',
#                wrap(self.add_view),
#                name='%s_%s_add' % info),
            url(r'^daily-burn-program/fire$',
                wrap(self.fireload_view),
                name='fireload_view'),

        )
        return urlpatterns + super(FireAdmin, self).get_urls()


    def fireload_view(self, request, extra_context=None):
        """
        Current fireLoad. Display a list of the current day fires
        by chaining querysets PrescribedBurn and Fire to a single queryset
        """

        if request.REQUEST.has_key('date'):
            dt = request.REQUEST.get('date', None)
            if dt:
                dt = datetime.strptime(dt, '%Y-%m-%d')
        else:
            dt = date.today()
            time_now = datetime.now().time()
            if time_now.hour > settings.DAY_ROLLOVER_HOUR:
                dt = dt + timedelta(days=1)


        qs_burn = PrescribedBurn.objects.filter(date=dt).exclude(status=PrescribedBurn.BURN_PLANNED)
        qs_fire = Fire.objects.filter(date=dt)

        title = "Summary of Current Fire Load"
        form = FireLoadForm(request.GET)

        fire_type = 0
        if request.REQUEST.has_key('fire_type'):
            fire_type = int (request.REQUEST.get('fire_type', None))

        #import ipdb; ipdb.set_trace()
        if request.REQUEST.has_key('region'):
            region = request.REQUEST.get('region', None)
            if region:
                qs_burn = qs_burn.filter(prescription__region=region)
                qs_fire = qs_fire.filter(region=region)

        if request.REQUEST.has_key('district'):
            district = request.REQUEST.get('district', None)
            if district:
                qs_burn = qs_burn.filter(prescription__district=district)
                qs_fire = qs_fire.filter(district=district)

        def qs_fireload(qs_burn, qs_fire, fire_type):
            """ concatenate two queysets (if fire_type is ALL) """
            if fire_type == 1:
                return qs_burn
            elif fire_type == 2:
                return qs_fire
            return list(itertools.chain(qs_burn, qs_fire))

        context = {
            'title': title,
            'qs_fireload': qs_fireload(qs_burn, qs_fire, fire_type),
            'form': form,
            'report': 'epfp_fireload',
            'username': request.user.username,
            'date': dt.strftime('%Y-%m-%d'),
            'fire_type': fire_type,

            'active_burns_statewide': PrescribedBurn.objects.filter(status=PrescribedBurn.BURN_ACTIVE, date=dt).count(),
            'active_burns_non_statewide': PrescribedBurn.objects.filter(status=PrescribedBurn.BURN_ACTIVE, date=dt, prescription__region__in=[6, 7, 8]).count(),
            'active_fires_statewide': Fire.objects.filter(active=True, date=dt).count(),
            'active_fires_non_statewide': Fire.objects.filter(active=True, date=dt, region__in=[6, 7, 8]).count(),

        }
        context.update(extra_context or {})
        return TemplateResponse(request, "admin/epfp_daily_burn_program.html", context)


