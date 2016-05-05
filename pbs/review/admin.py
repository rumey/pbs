from pbs.admin import BaseAdmin
from swingers.admin import DetailAdmin
from functools import update_wrapper
from django.contrib.auth.models import Group
from django.template.response import TemplateResponse

from pbs.review.models import BurnState, PrescribedBurn, Fire
from pbs.review.forms import BurnStateSummaryForm, PrescribedBurnForm, PrescribedBurnEditForm, FireLoadFilterForm, PrescribedBurnFilterForm
from pbs.prescription.models import Prescription, Approval
from datetime import datetime, date, timedelta
from django.utils import timezone
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse
import itertools
from django.contrib.admin.util import quote, unquote, flatten_fieldsets
from django.conf import settings
from pbs.admin import BaseAdmin
from pbs.prescription.admin import PrescriptionMixin
from django.contrib import admin
from functools import update_wrapper, partial
from django.core.exceptions import (FieldError, ValidationError,
                                    PermissionDenied)
from django.forms.models import modelform_factory
import json

import logging
logger = logging.getLogger('pbs')

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

from pbs.prescription.actions import delete_selected, archive_documents
class PrescribedBurnAdmin(DetailAdmin, BaseAdmin):
    #fields = ("prescription", "date", "status", "further_ignitions", "external_assist", "planned_area", "area", "tenures", "location", "est_start", "conditions")

    srm_group = Group.objects.get(name='State Regional Manager')
    sdo_group = Group.objects.get(name='State Duty Officer')

    #form = PrescribedBurnForm

    def get_form(self, request, obj=None, **kwargs):
        #import ipdb; ipdb.set_trace()
        if obj:
            return PrescribedBurnEditForm
        else:
            return PrescribedBurnForm

    def save_model(self, request, obj, form, change=True):
        """ Form does not assign user, do it here """
        #obj.user = request.user
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
            url(r'^review/(\d+)/$',
                wrap(self.changelist_view),
                #name='%s_%s_changelist' % info),
                name='review_review_changelist'),
            url(r'^add/burn/(\d+)/$',
                wrap(self.add_view),
                name='%s_%s_add' % info),
            url(r'^daily-burn-program/$',
                wrap(self.daily_burn_program),
                name='daily_burn_program'),
            url(r'^daily-burn-program/fire_action',
                wrap(self.action_view),
                name='action_view'),

            url(r'^daily-burn-program/test',
                wrap(self.test_view),
                name='test_view'),

            url(r'^daily-burn-program/epfp',
                wrap(self.prescription_view),
                name='prescription_view'),
            url(r'^daily-burn-program/copy_records',
                wrap(self.copy_records),
                name='copy_records'),

        )
        return urlpatterns + super(PrescribedBurnAdmin, self).get_urls()

    def change_view(self, request, object_id, extra_context=None):

#        if prescription is None:
#            raise Http404(_('prescription object with primary key %(key)r '
#                            'does not exist.') % {'key': prescription_id})
#
#        if request.method == 'POST' and "_saveasnew" in request.POST:
#            opts = self.model._meta
#            return self.add_view(request, prescription_id=prescription.id,
#                                 form_url=reverse(
#                                     'admin:%s_%s_add' %
#                                     (opts.app_label, opts.module_name),
#                                     args=[prescription.id],
#                                     current_app=self.admin_site.name))
#
#        context = {
#            'current': prescription
#        }
#        context.update(extra_context or {})
        obj = self.get_object(request, unquote(object_id))
        now = datetime.now()
        today = now.date()
        yesterday = today - timedelta(days=1)
        time_now = now.time()
        if obj.date < yesterday:
            self.message_user(request, "Past burns cannot be edited")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        if not self.has_change_permission(request, obj):
            self.message_user(request, "{} has no change permission".format(request.user))
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        # check lockout time
        if today >= obj.date and time_now.hour > settings.DAY_ROLLOVER_HOUR:
            # only SDO can edit current day's burn after cut-off hour.
            if self.sdo_group not in request.user.groups.all():
                self.message_user(request, "Only a SDO role can edit this burn (after cut-off hour - {}:00)".format(settings.DAY_ROLLOVER_HOUR))
                return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        if obj.approval_status == PrescribedBurn.APPROVAL_APPROVED:
            if self.sdo_group not in request.user.groups.all():
                self.message_user(request, "Only a SDO role can edit an APPROVED burn")
                return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


        context = {}
        context.update(extra_context or {})

        return super(PrescribedBurnAdmin, self).change_view(
            request, object_id, extra_context=context)



    def prescription_view(self, request, extra_context=None):
        if request.is_ajax():
            if request.REQUEST.has_key('burn_id'):
                burn_id = str( request.REQUEST.get('burn_id') )
#                if not burn_id or burn_id.startswith('---'):
#                    return
                logger.info('burn_id '.format(burn_id))
                p = Prescription.objects.filter(burn_id=burn_id)[0]
                tenures = ', '.join([i.name for i in p.tenures.all()])
                if len(p.location.split('|')) > 1:
                    tokens = p.location.split('|')
                    location = tokens[1] + 'km ' + tokens[2] + ' of ' + tokens[3]
                else:
                    #location = p.location
                    location = None

                return HttpResponse(json.dumps({"location": location, "tenures": tenures}))
                #return HttpResponse(json.dumps({"location": epfp.location}))
        return HttpResponse(json.dumps({"location": None, "tenures": None}))

    def test_view(self, request, extra_context=None):
        self.message_user(request, "My Test Message")
        #return HttpResponse(json.dumps({'errors': form.errors}))
        return HttpResponse(json.dumps({"redirect": request.META.get('HTTP_REFERER')}))

    #def action_view(self, request, object_id, form_url='', extra_context=None):
    #def action_view(self, request, *args, **kwargs):
    def action_view(self, request, extra_context=None):
        referrer_url = request.META.get('HTTP_REFERER')
        if request.POST.has_key('action'):
            action = request.POST['action']

            if request.POST.has_key('data'):
                if len(request.POST['data']) == 0: # and action != "Copy Records":
                    message = "No rows were selected"
                    msg_type = "danger"
                    return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": msg_type}))
                data = [int(i.strip()) for i in request.POST['data'].split(',')]
            else:
                raise Http404('Could not get Data/Row IDs')

            if request.POST.has_key('date'):
                dt = datetime.strptime(request.POST['date'], '%Y-%m-%d').date()
            else:
                raise Http404('Could not get Date')
        else:
            raise Http404('Could not get Update Action command')

        objects = PrescribedBurn.objects.filter(id__in=data)
        today = date.today()
        #today = date(2016,4,12)
        tomorrow = today + timedelta(days=1)
        yesterday = today - timedelta(days=1)
        if action == "Submit":
            not_draft = []
            for obj in objects:
                if obj.approval_status == obj.APPROVAL_DRAFT:
                    obj.submitted_by = request.user
                    obj.approval_status = obj.APPROVAL_SUBMITTED
                    obj.approval_status_modified = timezone.now()
                    obj.save()
                    #self.message_user(request, "Successfully submitted.")
                    count += 1
                    message = "Successfully submitted {} burn{}".format(count, "s" if count>1 else "")
                    msg_type = "success"
                else:
                    not_draft.append(obj.prescription.burn_id)

                if not_draft:
                    #self.message_user(request, "Could not submit {}\n. Only DRAFT burns can be SUBMITTED".format(', '.join(not_draft)))
                    message = "Could not submit {}\n. Only DRAFT burns can be SUBMITTED".format(', '.join(not_draft))
                    msg_type = "danger"
                    return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": msg_type}))

        elif action == "Endorse":
            if not ( self.srm_group in request.user.groups.all() or self.sdo_group in request.user.groups.all() ):
                message = "Only a SRM and SDO roles can ENDORSE burns"
                return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

            # TODO can approve records for today or tomorrow only?
            if not (dt == today or dt == tomorrow):
                message = "Can only endorse burns for today {}, or tomorrow {}.".format(today, tomorrow)
                msg_type = "danger"
                return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": msg_type}))
                #self.message_user(request, "Can only endorse burns for today {}, or tomorrow {}.".format(today, tomorrow))
                #return HttpResponse(json.dumps({"redirect": request.META.get('HTTP_REFERER')}))

            # Only Submitted plans can be endorsed
            #submitted_objects = PrescribedBurn.objects.filter(date=date, )

            not_submitted = []
            count = 0
            for obj in objects:
                if obj.approval_status == obj.APPROVAL_SUBMITTED:
                    obj.endorsed_by = request.user
                    obj.approval_status = obj.APPROVAL_ENDORSED
                    obj.approval_status_modified = timezone.now()
                    obj.save()
                    count += 1
                    message = "Successfully endorsed {} burn{}".format(count, "s" if count>1 else "")
                    msg_type = "success"
                else:
                    not_submitted.append(obj.prescription.burn_id)

                if not_submitted:
                    message = "Could not endorse {}\n. Only SUBMITTED burns can be endorsed".format(', '.join(not_submitted))
                    msg_type = "danger"
                    return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": msg_type}))

                    #self.message_user(request, "Could not endorse {}\n. Only SUBMITTED burns can be endorsed".format(', '.join(not_submitted)))
                    #return HttpResponse(json.dumps({"redirect": request.META.get('HTTP_REFERER')}))

        elif action == "Approve":

            if self.sdo_group not in request.user.groups.all():
                message = "Only a SDO role can APPROVED burns"
                return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

            if not (dt == today or dt == tomorrow):
                message = "Can only approve burns for today {}, or tomorrow {}.".format(today, tomorrow)
                return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

            #self.copy_records(yesterday, today)
            #unset_objects = self.check_rolled_records(today)
            #self.copy_records(request)
            unset_objects = self.check_rolled_records(dt)

            if len(unset_objects) > 0:
                message = "Copied burns from previous day have status/area field unset. Must set these before Approval.\n{}".format(
                    ', '.join([obj.prescription.burn_id for obj in unset_objects]))
                return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

            #import ipdb; ipdb.set_trace()
            not_endorsed = []
            count = 0
            for obj in objects:
                if obj.approval_status == obj.APPROVAL_ENDORSED:
                    obj.approved_by = request.user
                    obj.approval_status = obj.APPROVAL_APPROVED
                    obj.approval_status_modified = timezone.now()
                    obj.save()
                    count += 1
                    message = "Successfully approved {} burn{}".format(count, "s" if count>1 else "")
                    msg_type = "success"
                    #self.message_user(request, "Successfully submitted for approved")
                else:
                    not_endorsed.append(obj.prescription.burn_id)

                if not_endorsed:
                    message = "Could not approve {}\n. Only ENDORSED burns can be approved".format(', '.join(not_endorsed))
                    return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

        elif action == "Delete Approve":
            if self.sdo_group not in request.user.groups.all():
                message = "Only a SDO role can delete an APPROVAL"
                return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

            count = 0
            for obj in objects:
                if obj.approval_status == obj.APPROVAL_APPROVED:
                    obj.approved_by = None
                    obj.approval_status = obj.APPROVAL_ENDORSED
                    obj.approval_status_modified = timezone.now()
                    obj.save()
                    count += 1
                    message = "Successfully deleted {} approval{}".format(count, "s" if count>1 else "")
                    msg_type = "success"
            if count == 0:
                message = "No records deleted"
                msg_type = "info"

        elif action == "Delete Endorse":
            if not ( self.srm_group in request.user.groups.all() or self.sdo_group in request.user.groups.all() ):
                message = "Only a SRM and SDO roles can delete an ENDORSEMENT"
                return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

            count = 0
            for obj in objects:
                if obj.approval_status == obj.APPROVAL_ENDORSED:
                    obj.endorsed_by = None
                    obj.approval_status = obj.APPROVAL_SUBMITTED
                    obj.approval_status_modified = timezone.now()
                    obj.save()
                    count += 1
                    message = "Successfully deleted {} endorsement{}".format(count, "s" if count>1 else "")
                    msg_type = "success"
            if count == 0:
                message = "No records deleted"
                msg_type = "info"

        elif action == "Delete Submit":
            count = 0
            for obj in objects:
                if obj.approval_status == obj.APPROVAL_SUBMITTED:
                    obj.submitted_by = None
                    obj.approval_status = obj.APPROVAL_DRAFT
                    obj.approval_status_modified = timezone.now()
                    obj.save()
                    count += 1
                    message = "Successfully deleted {} submitted burn{}".format(count, "s" if count>1 else "")
                    msg_type = "success"
            if count == 0:
                message = "No records deleted"
                msg_type = "info"

        return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": msg_type}))

    def daily_burn_program(self, request, extra_context=None):
        """
        Display a list of the current day's planned burns
        """
        #import ipdb; ipdb.set_trace()
        report_set = {'epfp_planned', 'epfp_fireload', 'epfp_summary'}
        report = request.GET.get('report', 'epfp_planned')
        if report not in report_set:
            report = 'epfp_planned'

        if request.REQUEST.has_key('report'):
            report = request.REQUEST.get('report', None)

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

        yesterday = dt - timedelta(days=1)

#        queryset= None
        #import ipdb; ipdb.set_trace()
        #qs_planned = PlannedBurn.objects.filter(date=dt)
        qs_burn = PrescribedBurn.objects.filter(date=dt)
        qs_fire = Fire.objects.filter(date=dt)
        #qs_fireload = FireLoad.objects.filter(prescription__date=dt, fire__date=dt)
        if report=='epfp_planned':
            title = "Today's Planned Burn Program"
            # assumes all burns entered on date dt are planned (for date dt)
            #qs_burn = qs_burn.filter(status=PrescribedBurn.BURN_PLANNED).exclude(rolled=True)
            #qs_burn = qs_burn.exclude(rolled=True)
            form = PrescribedBurnFilterForm(request.GET)
            #form = PrescribedBurnForm(request.GET)
#            pb = PrescribedBurn(user=request.user)
            #form = PlannedBurnForm(initial={'user': request.user})
            #form = PlannedBurnForm(request.POST or None, request=request)
#            if form.is_valid():
#                pb.save()
        elif report=='epfp_fireload':
            title = "Summary of Current Fire Load"
            qs_burn = PrescribedBurn.objects.filter(date=yesterday, status__in=[PrescribedBurn.BURN_ACTIVE, PrescribedBurn.BURN_INACTIVE])
            qs_fire = Fire.objects.filter(date=yesterday)
            form = FireLoadFilterForm(request.GET)
            #form = FireLoadForm(request.GET)
        elif report=='epfp_summary':
            title = "Summary of Current and Planned Fires"
            qs_burn = qs_burn.filter(status__in=[PrescribedBurn.BURN_PLANNED, PrescribedBurn.BURN_ACTIVE], approval_status=PrescribedBurn.APPROVAL_APPROVED)
            qs_fire = qs_fire.filter(active=True)
            #qs_fire = qs_fireload.filter(prescription__active=True, fire__active=True)
            #qs_fireload = qs_fireload.filter(prescription__active=True, fire__active=True)
            form = PrescribedBurnFilterForm(request.GET)
            #form = FireLoadForm(request.GET)
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

        #import ipdb; ipdb.set_trace()
        if request.REQUEST.has_key('approval_status'):
            approval_status = map(int, request.REQUEST.getlist('approval_status'))
            if approval_status:
                if report=='epfp_planned':
                    qs_burn = qs_burn.filter(approval_status__in=approval_status)
                else:
                    qs_burn = qs_burn.filter(approval_status__in=approval_status)
                    qs_fire = qs_fire.filter(approval_status=approval_status)

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

    #def copy_records(self, today):
    def copy_records(self, request, extra_context=None):
        """
        Copy yesterday's 'active' records to today
        To be run via Cron?
        """

        if request.POST.has_key('date'):
            dt = datetime.strptime(request.POST['date'], '%Y-%m-%d').date()
        else:
            raise Http404('Could not get Date')

        today = date.today()
        tomorrow = today + timedelta(days=1)
        if not (dt == today or dt == tomorrow):
            message = "Can only copy records for today {}, or tomorrow {}.".format(today, tomorrow)
            return HttpResponse(json.dumps({"redirect": request.META.get('HTTP_REFERER'), "message": message, "type": "danger"}))

        # copy permitted only after given time, and only for today to tomorrow
#        if dt != today:
#            message = 'WARNING: Cannot copy for date {}. Can only copy planned burn records from yesterday {}, to today {}'.format(dt, yesterday, today)
#            logger.warn(message)
#            return

        #today = date.today()
        yesterday = dt - timedelta(days=1)
        yest_objects = [i.prescription.burn_id for i in PrescribedBurn.objects.filter(
            date=yesterday, status=PrescribedBurn.BURN_ACTIVE, approval_status__in=[PrescribedBurn.APPROVAL_ENDORSED, PrescribedBurn.APPROVAL_APPROVED])]
        copied_objects = PrescribedBurn.objects.filter(date=dt, prescription__burn_id__in=yest_objects)
        missing = list(set(yest_objects).difference(copied_objects))

        #import ipdb; ipdb.set_trace()
        count = 0
        for i in PrescribedBurn.objects.filter(prescription__burn_id__in=missing, date=yesterday):
            try:
                i.pk = None
                i.date = dt
                i.area = None
                i.status = 1
                i.approval_status = PrescribedBurn.APPROVAL_ENDORSED
                i.approved_by = None
                i.rolled = True
                i.save()
                count += 1
            except:
                # records already exist - pk (pres, date) will not allow overwrite, so ignore the exception
                logger.warn('WARNING: Record not copied. Record {} already exists on day {}'.format(i.prescription.burn_id, today))
                pass

        message = "{} records ".format(count)  if count > 1 else "{} record ".format(count) + "copied"
        return HttpResponse(json.dumps({"redirect": request.META.get('HTTP_REFERER'), "message": message, "type": "info"}))

    def check_rolled_records(self, today):
        """
        Verify Copied records have 'Active/Inactive' and 'Area' fields set,
        return list of objects that are unset
        """

        rolled_objects = PrescribedBurn.objects.filter(date=today, rolled=True)
        unset_objects = list(set(rolled_objects.filter(area__isnull=True)).union(rolled_objects.filter(status__isnull=True)))

        return unset_objects

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
        #obj.user = request.user
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
            url(r'^daily-burn-program/fire-submit',
                wrap(self.fire_submit),
                name='fire_submit'),
        )
        return urlpatterns + super(FireAdmin, self).get_urls()


    def fire_submit(self, request, extra_context=None):
        import ipdb; ipdb.set_trace()
        pass

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


