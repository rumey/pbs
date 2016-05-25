from pbs.admin import BaseAdmin
from swingers.admin import DetailAdmin
from functools import update_wrapper
from django.contrib.auth.models import Group, User
from django.template.response import TemplateResponse

from pbs.review.models import BurnState, PrescribedBurn, Acknowledgement
from pbs.review.forms import (BurnStateSummaryForm, PrescribedBurnForm, PrescribedBurnActiveForm, PrescribedBurnEditForm,
        FireLoadFilterForm, PrescribedBurnFilterForm, FireForm, FireEditForm
    )
from pbs.prescription.models import Prescription, Approval, Region
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
from django.contrib.admin import helpers
from django.utils.translation import ugettext as _, ugettext_lazy
import unicodecsv
import json
import os
from django.template.loader import render_to_string
from django.template import RequestContext
from django.db.models import Q
import subprocess
import sys, traceback
from django.db import IntegrityError

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

class PrescribedBurnAdmin(DetailAdmin, BaseAdmin):
    #fields = ("prescription", "date", "status", "further_ignitions", "external_assist", "planned_area", "area", "tenures", "location", "est_start", "conditions")

    #srm_group = Group.objects.get(name='State Regional Manager')
    #sdo_group = Group.objects.get(name='State Duty Officer')

    #form = PrescribedBurnForm
    @property
    def srm_group(self):
        return Group.objects.get(name='State Regional Manager')

    @property
    def sdo_group(self):
        return Group.objects.get(name='State Duty Officer')

    def get_context_data(self, **kwargs):
        context = super(PrescribedBurnAdmin, self).get_context_data(**kwargs)
        #obj = self.get_object()
        context['title'] = ' 1234'

        return context

    def get_form(self, request, obj=None, **kwargs):
        #import ipdb; ipdb.set_trace()
        if request.GET.has_key('form'):
            if request.REQUEST.get('form')=='add_fire':
                return FireForm
            if request.REQUEST.get('form')=='edit_fire':
                return FireEditForm
            if request.REQUEST.get('form')=='add_burn':
                return PrescribedBurnForm
            if request.REQUEST.get('form')=='add_active_burn' or request.REQUEST.get('form')=='edit_active_burn':
                return PrescribedBurnActiveForm
            if request.REQUEST.get('form')=='edit_burn':
                return PrescribedBurnEditForm
#            from django.forms import inlineformset_factory
#            FireFormSet = inlineformset_factory(Fire, PrescribedBurn, fields=('date',))
#            return AddFireForm

#        elif obj:
#            return PrescribedBurnEditForm
#        else:
#            return PrescribedBurnForm

    def addfire_view(self, request):
        """
        A custom view to display section A1 of an ePFP.
        """
        if request.method == "POST":
            import ipdb; ipdb.set_trace()
        else:
            #form = PrescribedBurnForm()
            form = FireForm()
            formset = FireFormSet()
            fireform = FireForm()
            burnform = PrescribedBurnForm()

        admin_form = helpers.AdminForm(
            form, [(None, {'fields': list(form.base_fields)})],
            self.get_prepopulated_fields(request, None),
            self.get_readonly_fields(request, None),
            model_admin=self
        )
        media = self.media + admin_form.media

        context = {
            'form': admin_form,
            'formset': formset,
            'fireform': fireform,
            'burnform': burnform,
            'media': media,
        }

        addfire_template = 'admin/review/prescribedburn/add_fire.html'
        return TemplateResponse(request, addfire_template,
                                context, current_app=self.admin_site.name)


#    def save_model(self, request, obj, form, change=True):
#        if obj.prescription:
#            obj.form_name = 1
#        else:
#            obj.form_name = 2
#        obj.save()

    def response_post_save_change(self, request, obj):
        """
        Override the redirect url after successful save of an existing PrescribedBurn
        """
        #import ipdb; ipdb.set_trace()
        if 'edit_fire' in request.META.get('HTTP_REFERER') or 'edit_active_burn' in request.META.get('HTTP_REFERER'):
            url = reverse('admin:daily_burn_program') + '?report=epfp_fireload&date={}'.format(request.REQUEST['date'])
        elif 'edit_burn' in request.META.get('HTTP_REFERER'):
            url = reverse('admin:daily_burn_program') + '?report=epfp_planned&date={}'.format(request.REQUEST['date'])
        else:
            url = reverse('admin:daily_burn_program')

        return HttpResponseRedirect(url)

    def response_post_save_add(self, request, obj):
        """
        Override the redirect url after successful save of a new PrescribedBurn
        """
        if request.REQUEST.has_key('form'):
            if 'add_fire' in request.REQUEST['form'] or 'add_active_burn' in request.REQUEST['form']:
                url = reverse('admin:daily_burn_program') + '?report=epfp_fireload&date={}'.format(request.REQUEST['date'])
            if 'add_burn' in request.REQUEST['form']:
                url = reverse('admin:daily_burn_program') + '?report=epfp_planned&date={}'.format(request.REQUEST['date'])
        else:
            url = reverse('admin:daily_burn_program')

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
#            url(r'^daily-burn-program/copy_records',
#                wrap(self.copy_records),
#                name='copy_records'),
            url(r'^addfire',
                wrap(self.addfire_view),
                #name='%s_%s_add' % info),
                name='addfire_view'),
            url(r'^daily-burn-program/export_csv/$',
                wrap(self.export_to_csv),
                name='daily_burn_program_exportcsv'),
            url(r'^daily-burn-program/pdf',
                wrap(self.pdflatex),
                name='create_dailyburns_pdf'),

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
        #import ipdb; ipdb.set_trace()
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

        if obj.formA_sdo_acknowledged or obj.formB_sdo_acknowledged:
            if self.sdo_group not in request.user.groups.all():
                self.message_user(request, "Only a SDO role can edit an APPROVED burn")
                return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


        context = {}
        context.update(extra_context or {})

        return super(PrescribedBurnAdmin, self).change_view(
            request, object_id, extra_context=context)

#        url = reverse('admin:epfp_review_summary')
#        return HttpResponseRedirect(url)


    def prescription_view(self, request, extra_context=None):
        """
        Used for pre-populating location and tenures fields in PrescribedBurnForm, via ajax call
        """
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

    def action_view(self, request, extra_context=None):
        if request.REQUEST.has_key('report'):
            report = request.REQUEST.get('report', None)

        if request.POST.has_key('date'):
            dt = datetime.strptime(request.POST['date'], '%Y-%m-%d').date()
        else:
            raise Http404('Could not get Date')

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

        else:
            raise Http404('Could not get Update Action command')

        objects = PrescribedBurn.objects.filter(id__in=data)
        today = date.today()
        now = timezone.now()
        #today = date(2016,4,12)
        tomorrow = today + timedelta(days=1)
        yesterday = today - timedelta(days=1)
        if action == "Submit":
            count = 0
            if report=='epfp_planned':
                not_acknowledged = []
                already_acknowledged = []
                for obj in objects:
                    if obj.formA_isDraft:
                        if Acknowledgement.objects.filter(burn=obj, acknow_type='USER_A').count() == 0:
                            Acknowledgement.objects.get_or_create(burn=obj, user=request.user, acknow_type='USER_A', acknow_date=now)
                            obj.save()
                            count += 1
                            message = "Successfully acknowledged {} record{}".format(count, "s" if count>1 else "")
                            msg_type = "success"
                        else:
                            not_acknowledged.append(obj.fire_idd)

                    elif obj.formA_user_acknowledged:
                        already_acknowledged.append(obj.fire_idd)
                        message = "record already acknowledged {}".format(', '.join(already_acknowledged))
                        msg_type = "danger"

                if not_acknowledged:
                    message = "Could not acknowledge. First remove existing acknowledgment {}\n".format(', '.join(not_acknowledged))
                    return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

            elif report=='epfp_fireload':
                not_acknowledged = []
                already_acknowledged = []
                unset_acknowledged = []
                for obj in objects:
                    if obj.active:
                        if obj.area and obj.status:
                            if obj.formB_isDraft:
                                if Acknowledgement.objects.filter(burn=obj, acknow_type='USER_B').count() == 0:
                                    Acknowledgement.objects.get_or_create(burn=obj, user=request.user, acknow_type='USER_B', acknow_date=now)
                                    obj.save()
                                    count += 1
                                    message = "Successfully acknowledged {} record{}".format(count, "s" if count>1 else "")
                                    msg_type = "success"
                                else:
                                    not_acknowledged.append(obj.fire_idd)

                            elif obj.formB_user_acknowledged:
                                already_acknowledged.append(obj.fire_idd)
                                message = "record already acknowledged {}".format(', '.join(already_acknowledged))
                                msg_type = "danger"
                        else:
                            unset_acknowledged.append(obj.fire_idd)
                            message = "Cannot acknowledge {}. First set Area/Status field(s)".format(', '.join(unset_acknowledged))
                            msg_type = "danger"

                if not_acknowledged:
                    message = "Could not acknowledge. First remove existing acknowledgment {}\n".format(', '.join(not_acknowledged))
                    return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

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

            count = 0
            if report=='epfp_planned':
                not_acknowledged = []
                already_acknowledged = []
                for obj in objects:
                    if obj.formA_user_acknowledged:
                        if Acknowledgement.objects.filter(burn=obj, acknow_type='SRM_A').count() == 0:
                            Acknowledgement.objects.get_or_create(burn=obj, user=request.user, acknow_type='SRM_A', acknow_date=now)
                            obj.save()
                            count += 1
                            message = "Successfully acknowledged {} record{}".format(count, "s" if count>1 else "")
                            msg_type = "success"
                        else:
                            not_acknowledged.append(obj.fire_idd)

                    elif obj.formA_srm_acknowledged:
                        already_acknowledged.append(obj.fire_idd)
                        message = "record already acknowledged {}".format(', '.join(already_acknowledged))
                        msg_type = "danger"

                if not_acknowledged:
                    message = "Could not acknowledge. First remove existing acknowledgment {}\n".format(', '.join(not_acknowledged))
                    return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

            elif report=='epfp_fireload':
                not_acknowledged = []
                already_acknowledged = []
                for obj in objects:
                    if obj.active:
                        if obj.formB_user_acknowledged:
                            if Acknowledgement.objects.filter(burn=obj, acknow_type='SRM_B').count() == 0:
                                Acknowledgement.objects.get_or_create(burn=obj, user=request.user, acknow_type='SRM_B', acknow_date=now)
                                obj.save()
                                count += 1
                                message = "Successfully acknowledged {} record{}".format(count, "s" if count>1 else "")
                                msg_type = "success"
                            else:
                                not_acknowledged.append(obj.fire_idd)

                        elif obj.formB_srm_acknowledged:
                            already_acknowledged.append(obj.fire_idd)
                            message = "record already acknowledged {}".format(', '.join(already_acknowledged))
                            msg_type = "danger"

                if not_acknowledged:
                    message = "Could not acknowledge. First remove existing acknowledgment {}\n".format(', '.join(not_acknowledged))
                    return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

        elif action == "Approve":

            if self.sdo_group not in request.user.groups.all():
                message = "Only a SDO role can APPROVED burns"
                return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

            if not (dt == today or dt == tomorrow):
                message = "Can only approve burns for today {}, or tomorrow {}.".format(today, tomorrow)
                return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

            # copy yesterdays ongoing active records to today
            if report=='epfp_planned':
                self.copy_ongoing_records(dt)
                unset_objects = self.check_rolled_records(dt)

                if len(unset_objects) > 0:
                    message = "Copied burns from previous day have status/area field unset. Must set these before Approval.\n{}".format(
                        ', '.join([obj.prescription.burn_id for obj in unset_objects]))
                    return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

            #import ipdb; ipdb.set_trace()
            count = 0
            if report=='epfp_planned':
                not_acknowledged = []
                already_acknowledged = []
                for obj in objects:
                    if obj.formA_srm_acknowledged:
                        if Acknowledgement.objects.filter(burn=obj, acknow_type='SDO_A').count() == 0:
                            Acknowledgement.objects.get_or_create(burn=obj, user=request.user, acknow_type='SDO_A', acknow_date=now)
                            obj.save()
                            count += 1
                            message = "Successfully acknowledged {} record{}".format(count, "s" if count>1 else "")
                            msg_type = "success"
                        else:
                            not_acknowledged.append(obj.fire_idd)

                    elif obj.formA_sdo_acknowledged:
                        already_acknowledged.append(obj.fire_idd)
                        message = "record already acknowledged {}".format(', '.join(already_acknowledged))
                        msg_type = "danger"

                if not_acknowledged:
                    message = "Could not acknowledge. First remove existing acknowledgment {}\n".format(', '.join(not_acknowledged))
                    return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

            elif report=='epfp_fireload':
                not_acknowledged = []
                already_acknowledged = []
                for obj in objects:
                    if obj.active:
                        if obj.formB_srm_acknowledged:
                            if Acknowledgement.objects.filter(burn=obj, acknow_type='SDO_B').count() == 0:
                                Acknowledgement.objects.get_or_create(burn=obj, user=request.user, acknow_type='SDO_B', acknow_date=now)
                                obj.save()
                                count += 1
                                message = "Successfully acknowledged {} record{}".format(count, "s" if count>1 else "")
                                msg_type = "success"
                            else:
                                not_acknowledged.append(obj.fire_idd)

                        elif obj.formB_sdo_acknowledged:
                            already_acknowledged.append(obj.fire_idd)
                            message = "record already acknowledged {}".format(', '.join(already_acknowledged))
                            msg_type = "danger"

                if not_acknowledged:
                    message = "Could not acknowledge. First remove existing acknowledgment {}\n".format(', '.join(not_acknowledged))
                    return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

        elif action == "Delete Approve":
            if self.sdo_group not in request.user.groups.all():
                message = "Only a SDO role can delete an APPROVAL"
                return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

            count = 0
            for obj in objects:
                if report=='epfp_planned':
                    if obj.formA_sdo_acknowledged:
                        ack = Acknowledgement.objects.filter(burn=obj, acknow_type='SDO_A')
                        if ack:
                            ack[0].delete()
                            obj.save()
                            count += 1
                            message = "Successfully deleted {} approval{}".format(count, "s" if count>1 else "")
                            msg_type = "success"
                else:
                    if obj.formB_sdo_acknowledged:
                        ack = Acknowledgement.objects.filter(burn=obj, acknow_type='SDO_B')
                        if ack:
                            ack[0].delete()
                            obj.save()
                            count += 1
                            message = "Successfully deleted {} approval{}".format(count, "s" if count>1 else "")
                            msg_type = "success"

            if count == 0:
                message = "No 'Approved' records were removed"
                msg_type = "info"

        elif action == "Delete Endorse":
            if not ( self.srm_group in request.user.groups.all() or self.sdo_group in request.user.groups.all() ):
                message = "Only a SRM and SDO roles can delete an ENDORSEMENT"
                return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

            count = 0
            for obj in objects:
                if report=='epfp_planned':
                    if obj.formA_srm_acknowledged:
                        ack = Acknowledgement.objects.filter(burn=obj, acknow_type='SRM_A')
                        if ack:
                            ack[0].delete()
                            obj.save()
                            count += 1
                            message = "Successfully deleted {} endorsement{}".format(count, "s" if count>1 else "")
                            msg_type = "success"
                else:
                    if obj.formB_srm_acknowledged:
                        ack = Acknowledgement.objects.filter(burn=obj, acknow_type='SRM_B')
                        if ack:
                            ack[0].delete()
                            obj.save()
                            count += 1
                            message = "Successfully deleted {} endorsement{}".format(count, "s" if count>1 else "")
                            msg_type = "success"

            if count == 0:
                message = "No 'Endorsed' records were removed"
                msg_type = "info"

        elif action == "Delete Submit":
            count = 0
            for obj in objects:
                if report=='epfp_planned':
                    if obj.formA_user_acknowledged:
                        ack = Acknowledgement.objects.filter(burn=obj, acknow_type='USER_A')
                        if ack:
                            ack[0].delete()
                            obj.save()
                            count += 1
                            message = "Successfully deleted {} submitted burn{}".format(count, "s" if count>1 else "")
                            msg_type = "success"
                else:
                    if obj.formB_user_acknowledged:
                        ack = Acknowledgement.objects.filter(burn=obj, acknow_type='USER_A')
                        ack = Acknowledgement.objects.filter(burn=obj, acknow_type='USER_B')
                        if ack:
                            ack[0].delete()
                            obj.save()
                            count += 1
                            message = "Successfully deleted {} submitted burn{}".format(count, "s" if count>1 else "")
                            msg_type = "success"

            if count == 0:
                message = "No records 'Submitted' status removed"
                msg_type = "info"

        elif action == "Delete Record":
            for obj in objects:
                if obj.formA_sdo_acknowledged or obj.formB_sdo_acknowledged:
                    if self.sdo_group not in request.user.groups.all():
                        self.message_user(request, "Only a SDO role can delete an APPROVED burn")
                        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

            count = objects.count()
            objects.delete()
            if objects.count() == 0:
                message = "Successfully deleted {} submitted burn{}".format(count, "s" if count>1 else "")
                msg_type = "success"
            else:
                message = "Failed to delete {} submitted burn{} (Records: {})".format(
                    objects.count(),
                    "s" if objects.count()>1 else "",
                    ', '.join([i.fire_id for i in objects])
                )
                msg_type = "danger"

        elif action == "Copy Record to Tomorrow":
            if not (dt >= yesterday or dt <= tomorrow):
                message = "Can only copy records for yesterday {}, today {}, or tomorrow {}.".format(yesterday, today, tomorrow)
                msg_type = "danger"
            else:
                count = self.copy_planned_records(dt, objects)
                message = "{} record{} copied".format(count, "s" if count > 1 else "")
                msg_type = "info"

        elif action == "Set Active":
            count = 0
            for obj in objects:
                obj.status = PrescribedBurn.BURN_ACTIVE
                obj.save()
                count += 1
                message = "Successfully set {} record{} ACTIVE".format(count, "s" if count>1 else "")
                msg_type = "success"

            if count == 0:
                message = "No records were modified"
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

        if request.GET.get('Export_CSV') == 'export_csv':
            return self.export_to_csv(request, dt)
#        queryset= None
        #import ipdb; ipdb.set_trace()
        #qs_planned = PlannedBurn.objects.filter(date=dt)
        qs_burn = PrescribedBurn.objects.filter(date=dt)
        #qs_fire = Fire.objects.filter(date=dt)
        #qs_fireload = FireLoad.objects.filter(prescription__date=dt, fire__date=dt)
        if report=='epfp_planned':
            title = "Today's Planned Burn Program"
            # assumes all burns entered on date dt are planned (for date dt)
            #qs_burn = qs_burn.exclude(rolled=True)
            qs_burn = qs_burn.filter(form_name=PrescribedBurn.FORM_268A)
            form = PrescribedBurnFilterForm(request.GET)
            #form = PrescribedBurnForm(request.GET)
#            pb = PrescribedBurn(user=request.user)
            #form = PlannedBurnForm(initial={'user': request.user})
            #form = PlannedBurnForm(request.POST or None, request=request)
#            if form.is_valid():
#                pb.save()
        elif report=='epfp_fireload':
            title = "Summary of Current Fire Load"
            #qs_burn = qs_burn.filter(status__in=[PrescribedBurn.BURN_ACTIVE, PrescribedBurn.BURN_INACTIVE, None], form_name=PrescribedBurn.FORM_268B)
            qs_burn = qs_burn.filter(form_name=PrescribedBurn.FORM_268B).exclude(status=PrescribedBurn.BURN_COMPLETED)
            #s_fire = Fire.objects.filter(date=yesterday)
            form = FireLoadFilterForm(request.GET)
            #form = FireLoadForm(request.GET)
        elif report=='epfp_summary':
            # Form 268c contains:
            #   1. SDO Approved Plans (Form A)
            #   2. SDO Approved Fireload (Form B)
            #   3. Only Burns (No Fires)
            title = "Summary of Current and Planned Fires"
            qs_burn = qs_burn.filter(acknowledgements__acknow_type__in=['SDO_A', 'SDO_B'], date=dt).exclude(prescription__isnull=True)
#            qs_burn = qs_burn.filter((Q(status=PrescribedBurn.BURN_ACTIVE) & Q(approval_268b_status=PrescribedBurn.APPROVAL_APPROVED)) |
#                                      Q(approval_268a_status=PrescribedBurn.APPROVAL_APPROVED),
#                                      date=dt).exclude(prescription__isnull=True).exclude(status=PrescribedBurn.BURN_INACTIVE)
            form = PrescribedBurnFilterForm(request.GET)

        fire_type = 0
        if request.REQUEST.has_key('fire_type'):
            fire_type = int (request.REQUEST.get('fire_type', None))
            if fire_type == 1:
                qs_burn = qs_burn.filter(fire_id__isnull=True)
            elif fire_type == 2:
                qs_burn = qs_burn.filter(prescription__isnull=True)


        #import ipdb; ipdb.set_trace()
        if request.REQUEST.has_key('region'):
            region = request.REQUEST.get('region', None)
            if region:
                #qs_burn = qs_burn.filter(prescription__region=region)
                qs_burn = qs_burn.filter(region=region)

        if request.REQUEST.has_key('district'):
            district = request.REQUEST.get('district', None)
            if district:
                #qs_burn = qs_burn.filter(prescription__district=district)
                qs_burn = qs_burn.filter(district=district)

        #import ipdb; ipdb.set_trace()
        if request.REQUEST.has_key('approval_status'):
            approval_status = map(str, request.REQUEST.getlist('approval_status'))
            if approval_status and len(approval_status)!=4:
                if report=='epfp_planned':
                    if len(approval_status)==1 and approval_status[0]=='DRAFT':
                        approval_choices = [i[0]+'_A' for i in PrescribedBurn.APPROVAL_CHOICES if i[0]!='DRAFT']
                        qs_burn = qs_burn.filter(form_name=PrescribedBurn.FORM_268A).exclude(acknowledgements__acknow_type__in=approval_choices).distinct()
                    else:
                        approval_choices = [i+'_A' for i in approval_status]
                        qs_burn = qs_burn.filter(acknowledgements__acknow_type__in=approval_choices, form_name=PrescribedBurn.FORM_268A).distinct()
                elif report=='epfp_fireload':
                    if len(approval_status)==1 and approval_status[0]=='DRAFT':
                        approval_choices = [i[0]+'_B' for i in PrescribedBurn.APPROVAL_CHOICES if i[0]!='DRAFT']
                        qs_burn = qs_burn.filter(form_name=PrescribedBurn.FORM_268B).exclude(acknowledgements__acknow_type__in=approval_choices).distinct()
                    else:
                        approval_choices = [i+'_B' for i in approval_status]
                        qs_burn = qs_burn.filter(acknowledgements__acknow_type__in=approval_choices, form_name=PrescribedBurn.FORM_268B).distinct()

#        def qs_fireload(qs_burn, qs_fire, fire_type):
#            if fire_type == 1:
#                return qs_burn
#            elif fire_type == 2:
#                return qs_fire
#            return list(itertools.chain(qs_burn, qs_fire))

        context = {
            'title': title,
            #'qs_burn': qs_burn.order_by('prescription__burn_id') if qs_burn else [],
            'qs_burn': qs_burn, # if qs_burn else [],
            'qs_fireload': qs_burn, #qs_fireload(qs_burn, qs_fire, fire_type),
            'form': form,
            'report': report,
            'username': request.user.username,
            'date': dt.strftime('%Y-%m-%d'),
            'fire_type': fire_type,

            'active_records': self.active_records(dt),
        }
        context.update(extra_context or {})
        return TemplateResponse(request, "admin/epfp_daily_burn_program.html", context)


    #def copy_ongoing_records(self, request, extra_context=None):

    def active_records(self, dt):
        qs_active = PrescribedBurn.objects.filter(status=PrescribedBurn.BURN_ACTIVE, date=dt)

        records = {
            "active_burns_statewide": qs_active.exclude(prescription__isnull=True).count(),
            "active_burns_non_statewide": qs_active.filter(region__in=[6, 7, 8]).exclude(prescription__isnull=True).count(),
            "active_fires_statewide": qs_active.exclude(fire_id__isnull=True).count(),
            "active_fires_non_statewide": qs_active.filter(region__in=[6, 7, 8]).exclude(fire_id__isnull=True).count(),
        }
        return records

    def copy_ongoing_records(self, dt):
        """
        Copy today's 'active' records to tomorrow

        268b - (Automatically) copy all records from yesterday that were Active when 268a Region Endorsement occurs,
        except for Active and Area Burnt Yesterday
        """

        today = date.today()
        tomorrow = today + timedelta(days=1)
        if not (dt == today or dt == tomorrow):
            # Can only copy records for today, or tomorrow
            return

        # copy permitted only after given time, and only for today to tomorrow
#        if dt != today:
#            message = 'WARNING: Cannot copy for date {}. Can only copy planned burn records from yesterday {}, to today {}'.format(dt, yesterday, today)
#            logger.warn(message)
#            return

        #today = date.today()
        tomorrow = dt + timedelta(days=1) # relative to dt
        #objects = [i.prescription.burn_id for i in PrescribedBurn.objects.filter(date=dt, status=PrescribedBurn.BURN_ACTIVE)
#        ids = [i.id for i in PrescribedBurn.objects.filter(date=dt, status=PrescribedBurn.BURN_ACTIVE)
#            # date=dt, status=PrescribedBurn.BURN_ACTIVE, approval_268a_status__in=[PrescribedBurn.APPROVAL_ENDORSED, PrescribedBurn.APPROVAL_APPROVED])]
#        copied_objects = PrescribedBurn.objects.filter(date=tomorrow, prescription__burn_id__in=objects).exclude(form_name=PrescribedBurn.FORM_268B)
#        missing = list(set(objects).difference(copied_objects))

        objects = [obj for obj in PrescribedBurn.objects.filter(date=dt, status=PrescribedBurn.BURN_ACTIVE)]
        now = timezone.now()
        admin = User.objects.get(username='admin')
        count = 0
        #for i in PrescribedBurn.objects.filter(prescription__burn_id__in=missing, date=dt):
        for obj in objects:
            if obj.fire_id and PrescribedBurn.objects.filter(fire_id=obj.fire_id, date=tomorrow, form_name=PrescribedBurn.FORM_268B):
                # don't copy if already exists - since record is unique on Prescription (not fire_id)
                continue
            try:
                obj.pk = None
                obj.date = tomorrow
                obj.area = None
                obj.status = None
                obj.approval_268a_status = PrescribedBurn.APPROVAL_DRAFT
                obj.approval_268a_status_modified = now
                obj.approval_268b_status = PrescribedBurn.APPROVAL_DRAFT
                obj.approval_268b_status_modified = now
                obj.acknowledgements.all().delete()
                obj.rolled = True
                obj.save()
                count += 1
            except:
                # records already exist - pk (pres, date) will not allow overwrite, so ignore the exception
                logger.warn('WARNING: Record not copied. Record {} already exists on day {}'.format(obj.fire_idd, tomorrow))

    def copy_planned_records(self, dt, objects):
        """
        Copy today's 'planned' records to tomorrow
        """
        today = date.today()
        tomorrow = today + timedelta(days=1) # actual tomorrow's date

        #import ipdb; ipdb.set_trace()
        now = timezone.now()
        admin = User.objects.get(username='admin')
        tomorrow = dt + timedelta(days=1) # relative to dt
        count = 0
        for i in objects:
            try:
                i.pk = None
                i.date = tomorrow
                i.area = None
                i.status = 1
                i.approval_268a_status = PrescribedBurn.APPROVAL_DRAFT
                i.approval_268a_status_modified = now
                i.approval_268b_status = PrescribedBurn.APPROVAL_DRAFT
                i.approval_268b_status_modified = now
                i.rolled = True
                i.save()
                count += 1
            except:
                # records already exist - pk (pres, date) will not allow overwrite, so ignore the exception
                logger.warn('WARNING: Record not copied. Record {} already exists on day {}'.format(i.prescription.burn_id, tomorrow))
                traceback.print_exc(file=sys.stdout)
                pass

        return count

    def check_rolled_records(self, today):
        """
        Verify Copied records have 'Active/Inactive' and 'Area' fields set,
        return list of objects that are unset
        """

        rolled_objects = PrescribedBurn.objects.filter(date=today, rolled=True).exclude(form_name=PrescribedBurn.FORM_268A).exclude(status=PrescribedBurn.BURN_COMPLETED)
        unset_objects = list(set(rolled_objects.filter(area__isnull=True)).union(rolled_objects.filter(status__isnull=True)))

        return unset_objects

    def export_to_csv(self, request, extra_context=None):

        if request.GET.has_key('date'):
            report_date = datetime.strptime(request.GET.get('date'), '%Y-%m-%d').date()
        else:
            raise Http404('Could not get Date')

        query_list = []
        id_list = []

        for pb in PrescribedBurn.objects.filter(date=report_date):
            if pb.prescription:
                fire_id = pb.prescription.burn_id
                name = pb.prescription.name
                region = str(pb.prescription.region)
                district = str(pb.prescription.district)
            else:
                fire_id = pb.fire_id
                name = pb.fire_name
                region = str(pb.region)
                district = str(pb.district)

            fire_type = pb.fire_type
            dt = pb.date.strftime('%Y-%m-%d')
            burn_status = pb.get_status_display()
            further_ignitions = "Yes" if pb.further_ignitions else ""
            external_assist = ', '.join([i.name for i in pb.external_assist.all()])
            planned_area = pb.planned_area
            area = pb.area
            tenures = pb.tenures
            location = pb.location
            est_start = pb.est_start
            conditions = pb.conditions
            approval_268a_status = pb.get_approval_268a_status_display()
            approval_268a_status_modified = pb.approval_268a_status_modified.strftime('%Y-%m-%d %H:%M') if pb.approval_268a_status_modified else ""
            approval_268b_status = pb.get_approval_268b_status_display()
            approval_268b_status_modified = pb.approval_268b_status_modified.strftime('%Y-%m-%d %H:%M') if pb.approval_268b_status_modified else ""
            submitted = pb.submitted_by.get_full_name() + " " + pb.submitted_date_str if pb.submitted_by else ""
            endorsed = pb.endorsed_by.get_full_name() + " " + pb.endorsed_date_str if pb.endorsed_by else ""
            approved = pb.approved_by.get_full_name() + " " + pb.approved_date_str if pb.approved_by else ""
            rolled = "Yes" if pb.rolled else ""

            query_list.append([fire_id, name, region, district, fire_type,
                               dt, burn_status, further_ignitions, external_assist,
                               planned_area, area, tenures, location, est_start, conditions,
                               approval_268a_status, approval_268a_status_modified,
                               approval_268b_status, approval_268b_status_modified,
                               submitted, endorsed, approved, rolled])

        filename = 'export_daily_burn_program_{0}.csv'.format(report_date.strftime('%d%b%Y'))
        response = HttpResponse(content_type="text/csv")
        response['Content-Disposition'] = 'attachment; filename={}'.format(filename)
        writer = unicodecsv.writer(response, quoting=unicodecsv.QUOTE_ALL)

        writer.writerow(["Fire ID", "Name", "Region", "District", "Type",
            "Date", "Burn Status", "Further Ignitions", "External Assist",
            "Planned Area", "Actual Area", "Tenures", "Location", "Est Start", "Conditions",
            "Approval Status (268a)" , "Approval Status Modified (268a)",
            "Approval Status (268b)" , "Approval Status Modified (268b)",
            "Submitted", "Endorsed", "Approved", "Rolled"])

        for row in query_list:
            writer.writerow([unicode(s).encode("utf-8") for s in row])

        return response
    export_to_csv.short_description = ugettext_lazy("Export to CSV")

    def pdflatex(self, request):
        if request.GET.has_key('date'):
            report_date = datetime.strptime(request.GET.get('date'), '%Y-%m-%d').date()
        else:
            raise Http404('Could not get Date')
        prescribed_burns = PrescribedBurn.objects.filter(date=report_date).distinct()

        if request.GET.has_key('region'):
            region = request.GET.get('region', None)
            prescribed_burns = prescribed_burns.filter(prescription__region=region)

        planned_burns = prescribed_burns.filter(form_name=PrescribedBurn.FORM_268A, acknowledgements__acknow_type__in=['SDO_A']).exclude(prescription__isnull=True)
        fireload = prescribed_burns.filter(form_name=PrescribedBurn.FORM_268B, status=PrescribedBurn.BURN_ACTIVE, acknowledgements__acknow_type__in=['SDO_B'])

        def acknow(burns, acknow_type):
            acknowledgements = Acknowledgement.objects.filter(burn__in=burns, acknow_type=acknow_type).distinct()
            return ', '.join(set([i.user.get_full_name() for i in acknowledgements]))

        acknow_records ={
            'srm_A': acknow(planned_burns, 'SRM_A'),
            'sdo_A': acknow(planned_burns, 'SDO_A'),
            'srm_B': acknow(fireload, 'SRM_B'),
            'sdo_B': acknow(fireload, 'SDO_B')
        }
        #import ipdb; ipdb.set_trace()
        obj = Prescription.objects.get(id=620)
        template = request.GET.get("template", "pfp")
        response = HttpResponse(content_type='application/pdf')
        texname = template + ".tex"
        filename = template + ".pdf"
        now = timezone.localtime(timezone.now())
        timestamp = now.isoformat().rsplit(
            ".")[0].replace(":", "")
        #fire_id = obj.prescription.burn_id if obj.prescription else obj.fire_id
#        downloadname = "{0}_{1}_{2}_{3}".format(
#            obj.season.replace('/', '-'), "fire_id", timestamp, filename).replace(
#                ' ', '_')
        downloadname = "daily_burn_program"
        error_response = HttpResponse(content_type='text/html')
        errortxt = downloadname.replace(".pdf", ".errors.txt.html")
        error_response['Content-Disposition'] = (
            '{0}; filename="{1}"'.format(
            "inline", errortxt))

        subtitles = {
            #"daily_burn_program": "Part A - Daily Burn Program",
            "form268a": "268a - Planned Burns",
            "form268b": "268b - Fire Load",
            "form268c": "268c - Approved Burns",
        }
        embed = False if request.GET.get("embed") == "false" else True
        context = {
            'user': request.user.get_full_name(),
            'date': datetime.now().strftime('%d %b %Y'),
            'region': Region.objects.get(id=int(region)).name,
            'time': datetime.now().strftime('%H:%M'),
            'state_regional_manager': datetime.now().strftime('%H:%M'),
            'qs_planned_burns': planned_burns.order_by('prescription__burn_id'),
            'qs_fireload': fireload.order_by('prescription__burn_id'),
            'acknow_records': acknow_records,
            'active_records': self.active_records(report_date),
            'current': obj,
            'prescription': obj,
            'embed': embed,
            'headers': request.GET.get("headers", True),
            'title': request.GET.get("title", "Prescribed Fire Plan"),
            'subtitle': subtitles.get(template, ""),
            'timestamp': now,
            'downloadname': downloadname,
            'settings': settings,
            'baseurl': request.build_absolute_uri("/")[:-1]
        }
#        if request.GET.get("download", False) is False:
#            disposition = "inline"
#        else:
#            disposition = "attachment"
        disposition = "attachment"
        response['Content-Disposition'] = (
            '{0}; filename="{1}"'.format(
                disposition, downloadname))

        directory = os.path.join(settings.MEDIA_ROOT, 'prescriptions',
                                    str(obj.season), obj.burn_id + os.sep)
        if not os.path.exists(directory):
            logger.debug("Making a new directory: {}".format(directory))
            os.makedirs(directory)

        logger.debug('Starting  render_to_string step')
        err_msg = None
        try:
            output = render_to_string(
                "latex/" + template + ".tex", context,
                context_instance=RequestContext(request))
        except Exception as e:
            import traceback
            err_msg = u"PDF tex template render failed (might be missing attachments):"
            logger.debug(err_msg + "\n{}".format(e))

            error_response.write(err_msg + "\n\n{0}\n\n{1}".format(e,traceback.format_exc()))
            return error_response

#        import ipdb; ipdb.set_trace()
        with open(directory + texname, "w") as f:
            f.write(output.encode('utf-8'))
            logger.debug("Writing to {}".format(directory + texname))

        logger.debug("Starting PDF rendering process ...")
        cmd = ['latexmk', '-cd', '-f', '-silent', '-pdf', directory + texname]
        logger.debug("Running: {0}".format(" ".join(cmd)))
        subprocess.call(cmd)

#        if not os.path.exists(filename):
#            logger.debug("No PDF appeared to be rendered, returning the contents of the log instead.")
#            filename = filename.replace(".pdf", ".log")
#            error_response.write(open(filename).read())
#            return error_response

        logger.debug("Reading PDF output from {}".format(filename))
        response.write(open(directory + filename).read())
        logger.debug("Finally: returning PDF response.")
        return response




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


