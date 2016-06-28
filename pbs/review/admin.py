from pbs.admin import BaseAdmin
from swingers.admin import DetailAdmin
from functools import update_wrapper
from django.contrib.auth.models import Group, User
from django.template.response import TemplateResponse

from pbs.review.models import BurnState, PrescribedBurn, Acknowledgement
from pbs.review.forms import (BurnStateSummaryForm, PrescribedBurnForm, PrescribedBurnActiveForm, PrescribedBurnEditForm,
        PrescribedBurnEditActiveForm, FireLoadFilterForm, PrescribedBurnFilterForm, FireForm, FireEditForm, CsvForm
    )
from pbs.prescription.models import Prescription, Approval, Region, District
from datetime import datetime, date, timedelta
from django.utils import timezone
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse
import itertools
from django.contrib.admin.util import quote, unquote, flatten_fieldsets
from django.conf import settings
from pbs.admin import BaseAdmin
from pbs.prescription.admin import PrescriptionMixin
from django.contrib import admin, messages
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
from django.forms import ModelChoiceField

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

    @property
    def srm_group(self):
        return Group.objects.get(name='Regional Duty Officer')

    @property
    def sdo_group(self):
        return Group.objects.get(name='State Duty Officer')

    @property
    def sdo_assist_group(self):
        return Group.objects.get(name='State Duty Officer Assistant')

    def get_form(self, request, obj=None, **kwargs):
        if request.GET.has_key('form'):
            if request.REQUEST.get('form')=='add_fire':
                return FireForm
            if request.REQUEST.get('form')=='edit_fire':
                return FireEditForm
            if request.REQUEST.get('form')=='add_burn':
                return PrescribedBurnForm
            if request.REQUEST.get('form')=='add_active_burn':
                return PrescribedBurnActiveForm
            if request.REQUEST.get('form')=='edit_active_burn':
                return PrescribedBurnEditActiveForm
            if request.REQUEST.get('form')=='edit_burn':
                return PrescribedBurnEditForm

    def csv_view(self, request):
        """ view to render the FMSB Report form """
        context = {'form': CsvForm()}
        csv_template = 'admin/review/prescribedburn/csv_form.html'
        return TemplateResponse(request, csv_template, context, current_app=self.admin_site.name)

    def response_post_save_change(self, request, obj):
        """
        Override the redirect url after successful save of an existing PrescribedBurn
        """
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
            url(r'^daily-burn-program/epfp',
                wrap(self.prescription_view),
                name='prescription_view'),
            url(r'^daily-burn-program/export_csv/$',
                wrap(self.export_to_csv),
                name='daily_burn_program_exportcsv'),
            url(r'^daily-burn-program/pdf',
                wrap(self.pdflatex),
                name='create_dailyburns_pdf'),
            url(r'^csv',
                wrap(self.csv_view),
                name='csv_view'),
            url(r'^bulk_delete/([\w\,]+)/$',
                wrap(self.bulk_delete),
                name='bulk_delete'),
            url(r'^help',
                wrap(self.help_view),
                name='help_view'),
        )
        return urlpatterns + super(PrescribedBurnAdmin, self).get_urls()

    def add_view(self, request, form_url='', extra_context=None):
        # default form title uses model name - need to do this to change name for the diff forms - since all are using the same model
        context = {'is_sdo': self.sdo_group in request.user.groups.all()}
        if request.GET.get('form') == 'add_fire':
            context.update({'form_title': 'Add Bushfire'})
        else:
            context.update({'form_title': 'Add Prescribed Burn'})

        context.update(extra_context or {})
        return super(PrescribedBurnAdmin, self).add_view(request, form_url, context)

    def change_view(self, request, object_id, extra_context=None):
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
            if self.sdo_group not in request.user.groups.all() and self.sdo_assist_group not in request.user.groups.all():
                self.message_user(request, "Only a SDO role can edit this burn (after cut-off hour - {}:00)".format(settings.DAY_ROLLOVER_HOUR))
                return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        if obj.formA_sdo_acknowledged or obj.formB_sdo_acknowledged:
            if self.sdo_group not in request.user.groups.all() and self.sdo_assist_group not in request.user.groups.all():
                self.message_user(request, "Only a 'SDO' or 'SDO Assist' role can edit an APPROVED burn")
                return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        # default form title uses model name - need to do this to change name for the diff forms - since all are using the same model
        context = {'is_sdo': self.sdo_group in request.user.groups.all()}
        if request.GET.get('form') == 'edit_fire':
            context.update({'form_title': 'Change Bushfire'})
        else:
            context.update({'form_title': 'Change Prescribed Burn'})

        return super(PrescribedBurnAdmin, self).change_view(
            request, object_id, extra_context=context)

    def delete_view(self, request, object_id, extra_context=None):
        """
        Redirect to main page on delete.
        """
        obj = self.get_object(request, unquote(object_id))
        if obj.formA_sdo_acknowledged or obj.formB_sdo_acknowledged:
            if self.sdo_group not in request.user.groups.all():
                self.message_user(request, "Only a SDO role can delete an APPROVED burn")
                return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        if obj.form_name==PrescribedBurn.FORM_268B and not (obj.status or obj.area):
            self.message_user(request, "Cannot delete a rolled record (record that was active or planned yesterday)", level=messages.ERROR)
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        response = super(PrescribedBurnAdmin, self).delete_view(request, object_id, extra_context)

        if isinstance(response, HttpResponseRedirect):
            url = reverse('admin:daily_burn_program')
            return HttpResponseRedirect(url)
        return response

    def prescription_view(self, request, extra_context=None):
        """
        Used for pre-populating location and tenures fields in PrescribedBurnForm, via ajax call
        also for calculating and returning the bushfire_id string for the FireForm
        """
        if request.is_ajax():
            if request.REQUEST.has_key('burn_id'):
                burn_id = str( request.REQUEST.get('burn_id') )
                logger.info('burn_id '.format(burn_id))
                p = Prescription.objects.filter(burn_id=burn_id)[0]
                tenures = ', '.join([i.name for i in p.tenures.all()])
                if len(p.location.split('|')) > 1:
                    tokens = p.location.split('|')
                    location = tokens[1] + 'km ' + tokens[2] + ' of ' + tokens[3]
                else:
                    #location = p.location
                    location = None

                d = {
                    "location": location,
                    "tenures": tenures,
                    "prescription_name": p.name,
                    "prescription_area": str(p.area),
                    }
                return HttpResponse(json.dumps(d))

            if request.REQUEST.has_key('fire_id'):
                # calculate and return the bushfire_id string for the FireForm
                fire_id = str( request.REQUEST.get('fire_id') )
                district_id = request.REQUEST.get('district')
                code = District.objects.get(id=district_id).code

                bushfire_id = code + '_' + fire_id
                return HttpResponse(json.dumps({'bushfire_id': bushfire_id}))

            if request.REQUEST.has_key('region'):
                qs = Prescription.objects.filter(burnstate__review_type__in=['FMSB'], planning_status=Prescription.PLANNING_APPROVED).filter(burnstate__review_type__in=['DRFMS']).distinct()
                qs = qs.filter(region=request.REQUEST.get('region')).order_by('burn_id')

                #burn_ids = ["<option value={}>{}</option>".format(p.id, p.burn_id) for p in qs]
                burn_ids = ModelChoiceField(queryset=qs).widget.render(value="pk_prescription", name="prescription")

        return HttpResponse(json.dumps({"location": None, "tenures": None, 'bushfire_id': None, 'burn_ids': burn_ids}))

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
        if action == "District Entered" or action == "District Submit":
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
                    message = "record already acknowledged {}".format(', '.join(not_acknowledged))
                    return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

            elif report=='epfp_fireload':
                not_acknowledged = []
                already_acknowledged = []
                unset_acknowledged = []
                for obj in objects:
                    if obj.area>=0 and obj.status:
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
                    message = "record already acknowledged {}".format(', '.join(not_acknowledged))
                    return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

        elif action == "Regional Acknowledgement" or action == "Regional Endorsement":
            if not ( self.srm_group in request.user.groups.all() or self.sdo_group in request.user.groups.all() ):
                message = "Only regional and state levels can acknowledge burns"
                return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

            # TODO can approve records for today or tomorrow only?
            if not (dt == today or dt == tomorrow):
                message = "Can only acknowledge burns for today {}, or tomorrow {}.".format(today, tomorrow)
                msg_type = "danger"
                return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": msg_type}))

            # Only Submitted plans can be endorsed
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

                    elif not obj.formA_user_acknowledged:
                        message = "record must first be submitted by district"
                        msg_type = "danger"

                    elif obj.formA_srm_acknowledged:
                        already_acknowledged.append(obj.fire_idd)
                        message = "record already acknowledged {}".format(', '.join(already_acknowledged))
                        msg_type = "danger"

                if not_acknowledged:
                    message = "record already acknowledged {}".format(', '.join(not_acknowledged))
                    return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

            elif report=='epfp_fireload':
                not_acknowledged = []
                already_acknowledged = []
                for obj in objects:
                    if obj.formB_user_acknowledged:
                        if Acknowledgement.objects.filter(burn=obj, acknow_type='SRM_B').count() == 0:
                            Acknowledgement.objects.get_or_create(burn=obj, user=request.user, acknow_type='SRM_B', acknow_date=now)
                            obj.save()
                            count += 1
                            message = "Successfully approved {} record{}".format(count, "s" if count>1 else "")
                            msg_type = "success"
                        else:
                            not_acknowledged.append(obj.fire_idd)

                    elif not obj.formB_user_acknowledged:
                        message = "record must first be submitted by district"
                        msg_type = "danger"

                    elif obj.formB_srm_acknowledged:
                        already_acknowledged.append(obj.fire_idd)
                        message = "record already approved {}".format(', '.join(already_acknowledged))
                        msg_type = "danger"

                if not_acknowledged:
                    message = "record already approved {}".format(', '.join(not_acknowledged))
                    return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

        elif action == "State Acknowledgement" or action == "State Approval":
            burn_desc = "burns/bushfires" if action == "State Acknowledgement" else "burns"
            if self.sdo_group not in request.user.groups.all():
                message = "Only regional and state levels can acknowledge {}".format(burn_desc)
                return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

            if not (dt == today or dt == tomorrow):
                message = "Can only acknowledge {} for today {}, or tomorrow {}.".format(burn_desc, today, tomorrow)
                return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

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

                    elif not obj.formA_srm_acknowledged:
                        message = "record must first be regionally acknowledged"
                        msg_type = "danger"

                    elif obj.formA_sdo_acknowledged:
                        already_acknowledged.append(obj.fire_idd)
                        message = "record already acknowledged {}".format(', '.join(already_acknowledged))
                        msg_type = "danger"

                if not_acknowledged:
                    message = "record already acknowledged {}".format(', '.join(not_acknowledged))
                    return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

                self.copy_planned_approved_records(dt)

            elif report=='epfp_fireload':
                self.copy_ongoing_records(dt) # copy yesterdays ongoing active records to today
                unset_objects = self.check_rolled_records(dt) # check records are correctly set
                if len(unset_objects) > 0:
                    message = "Copied burns from previous day have status/area field unset. Must set these before Approval.\n{}".format(
                        ', '.join([obj.fire_idd for obj in unset_objects]))
                    return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

                not_acknowledged = []
                already_acknowledged = []
                for obj in objects:
                    if obj.formB_srm_acknowledged:
                        if Acknowledgement.objects.filter(burn=obj, acknow_type='SDO_B').count() == 0:
                            Acknowledgement.objects.get_or_create(burn=obj, user=request.user, acknow_type='SDO_B', acknow_date=now)
                            obj.save()
                            count += 1
                            message = "Successfully approved {} record{}".format(count, "s" if count>1 else "")
                            msg_type = "success"
                        else:
                            not_acknowledged.append(obj.fire_idd)

                    elif not obj.formB_srm_acknowledged:
                        message = "record must first be regionally approved"
                        msg_type = "danger"

                    elif obj.formB_sdo_acknowledged:
                        already_acknowledged.append(obj.fire_idd)
                        message = "record already approved {}".format(', '.join(already_acknowledged))
                        msg_type = "danger"

                if not_acknowledged:
                    message = "record already approved {}".format(', '.join(not_acknowledged))
                    return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": "danger"}))

        elif action == "Delete State Acknowledgement" or action == "Delete State Approval":
            if self.sdo_group not in request.user.groups.all():
                message = "Only state levels can delete state acknowledgements"
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

        elif action == "Delete Regional Acknowledgement" or action == "Delete Regional Endorsement":
            if not ( self.srm_group in request.user.groups.all() or self.sdo_group in request.user.groups.all() ):
                message = "Only regional and state levels can delete regional acknowledgements"
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

        elif action == "Delete District Entry" or action == "Delete District Submit":
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
                        ack = Acknowledgement.objects.filter(burn=obj, acknow_type='USER_B')
                        if ack:
                            ack[0].delete()
                            obj.save()
                            count += 1
                            message = "Successfully deleted {0} submitted burn{1}/bushfire{1}".format(count, "s" if count>1 else "")
                            msg_type = "success"

            if count == 0:
                message = "No records 'Submitted' status removed"
                msg_type = "info"

        elif action == "Delete Record":
            """ This function now dealt with by javascript --> which calls bulk_delete()"""
            pass

        elif action == "Copy Record to Tomorrow":
            if not (dt >= yesterday or dt <= tomorrow):
                message = "Can only copy records for yesterday {}, today {}, or tomorrow {}.".format(yesterday, today, tomorrow)
                msg_type = "danger"
            else:
                count = self.copy_planned_records(dt, objects)
                message = "{} record{} copied".format(count, "s" if count > 1 else "")
                msg_type = "info"

#        elif action == "Set Active":
#            count = 0
#            for obj in objects:
#                obj.status = PrescribedBurn.BURN_ACTIVE
#                obj.save()
#                count += 1
#                message = "Successfully set {} record{} ACTIVE".format(count, "s" if count>1 else "")
#                msg_type = "success"
#
#            if count == 0:
#                message = "No records were modified"
#                msg_type = "info"

        return HttpResponse(json.dumps({"redirect": referrer_url, "message": message, "type": msg_type}))

    def bulk_delete(self, request, object_ids, extra_context=None):
        """
        View to bulk delete prescribed burns/fires
        """
        burn_desc = "burns/bushfires" if 'epfp_fireload' in request.META.get('HTTP_REFERER') else "burns"
        object_ids = map(int, object_ids.split(','))
        #objects = PrescribedBurn.objects.filter(id__in=object_ids)
        objects = PrescribedBurn.objects.filter(Q(id__in=object_ids), ~Q(Q(status__isnull=True) & Q(area__isnull=True) & Q(form_name=PrescribedBurn.FORM_268B)))
        non_deletable_objects = PrescribedBurn.objects.filter(id__in=object_ids, status__isnull=True, area__isnull=True, form_name=PrescribedBurn.FORM_268B)
        for obj in objects:
            if obj.formA_sdo_acknowledged or obj.formB_sdo_acknowledged:
                if self.sdo_group not in request.user.groups.all():
                    self.message_user(request, "Only state levels can delete a state acknowledged {}".format(burn_desc))
                    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        if request.method == 'POST':
            if objects:
                objects.delete()
                return HttpResponseRedirect(reverse('admin:daily_burn_program'))
            else:
                self.message_user(request, "Cannot delete rolled records (records that were active or planned yesterday)", level=messages.ERROR)
                return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        context = {
            'deletable_objects': objects,
            'non_deletable_objects': non_deletable_objects,
            'current': objects[0] if objects else None,
        }
        template = 'admin/review/prescribedburn/delete_selected_confirmation.html'
        return TemplateResponse(request, template, context) #, current_app=self.admin_site.name)

    def help_view(self, request, extra_context=None):
        return TemplateResponse(request, 'admin/review/prescribedburn/help.html', {'report': request.GET['report']})

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

        if request.REQUEST.has_key('date'):
            dt = request.REQUEST.get('date', None)
            if dt:
                dt = datetime.strptime(dt, '%Y-%m-%d')
        else:
            dt = date.today()
            time_now = datetime.now().time()
            if time_now.hour > settings.DAY_ROLLOVER_HOUR:
                dt = dt + timedelta(days=1)

        yesterday = dt - timedelta(days=1)

        qs_burn = PrescribedBurn.objects.filter(date=dt)
        if report=='epfp_planned':
            title = "Today's Planned Burn Program"
            # assumes all burns entered on date dt are planned (for date dt)
            qs_burn = qs_burn.filter(form_name=PrescribedBurn.FORM_268A)
            form = PrescribedBurnFilterForm(request.GET)
        elif report=='epfp_fireload':
            title = "Summary of Current Fire Load"
            qs_burn = qs_burn.filter(form_name=PrescribedBurn.FORM_268B)
            form = FireLoadFilterForm(request.GET)
        elif report=='epfp_summary':
            # Form 268c contains:
            #   1. SDO Approved Plans (Form A)
            #   2. SDO Approved Fireload (Form B)
            #   3. Only Burns (No Fires)
            title = "Summary of Current and Planned Fires"
            qs_burn = qs_burn.filter(acknowledgements__acknow_type='SDO_A', date=dt).exclude(prescription__isnull=True)
            form = PrescribedBurnFilterForm(request.GET)

        fire_type = 0
        if request.REQUEST.has_key('fire_type'):
            fire_type = int (request.REQUEST.get('fire_type', None))
            if fire_type == 1:
                qs_burn = qs_burn.filter(fire_id__isnull=True)
            elif fire_type == 2:
                qs_burn = qs_burn.filter(prescription__isnull=True)

        if request.REQUEST.has_key('region'):
            region = request.REQUEST.get('region', None)
            if region:
                qs_burn = qs_burn.filter(region=region)

        if request.REQUEST.has_key('district'):
            district = request.REQUEST.get('district', None)
            if district:
                qs_burn = qs_burn.filter(district=district)

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

        context = {
            'title': title,
            'qs_burn': qs_burn,
            'qs_fireload': qs_burn,
            'form': form,
            'report': report,
            'username': request.user.username,
            'date': dt.strftime('%Y-%m-%d'),
            'fire_type': fire_type,

            'active_records': self.active_records(dt),
        }
        context.update(extra_context or {})
        return TemplateResponse(request, "admin/epfp_daily_burn_program.html", context)

    def active_records(self, dt, region=None):
        qs_active = PrescribedBurn.objects.filter(status=PrescribedBurn.BURN_ACTIVE, form_name=PrescribedBurn.FORM_268B, date=dt)

        active_burns_statewide = qs_active.exclude(prescription__isnull=True)
        active_fires_statewide = qs_active.exclude(fire_id__isnull=True)

        records = {
            "active_burns_statewide": active_burns_statewide.count(),
            "active_burns_non_statewide": qs_active.filter(region__in=[6, 7, 8]).exclude(prescription__isnull=True).count(),
            "active_fires_statewide": active_fires_statewide.count(),
            "active_fires_non_statewide": qs_active.filter(region__in=[6, 7, 8]).exclude(fire_id__isnull=True).count(),

            "active_burns_region": active_burns_statewide.count() if not region else active_burns_statewide.filter(region=region).count(),
            "active_fires_region": active_fires_statewide.count() if not region else active_fires_statewide.filter(region=region).count(),
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


        tomorrow = dt + timedelta(days=1) # relative to dt
        objects = [obj for obj in PrescribedBurn.objects.filter(date=dt, status=PrescribedBurn.BURN_ACTIVE).exclude(ignition_status=PrescribedBurn.IGNITION_STATUS_COMPLETED)]
        now = timezone.now()
        admin = User.objects.get(username='admin')
        count = 0
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

    def copy_planned_approved_records(self, dt):
        """
        Copy today's 'planned' records (268a), that have been SDO approved. to tomorrow

        set Active and Area Burnt fields to None
        """

        today = date.today()
        tomorrow = today + timedelta(days=1)
        if not (dt == today or dt == tomorrow):
            # Can only copy records for today, or tomorrow
            return

        tomorrow = dt + timedelta(days=1) # relative to dt
        objects = PrescribedBurn.objects.filter(date=dt, acknowledgements__acknow_type__in=['SDO_A'], form_name=PrescribedBurn.FORM_268A)
        now = timezone.now()
        admin = User.objects.get(username='admin')
        count = 0
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
                #obj.acknowledgements.all().delete()
                obj.form_name=PrescribedBurn.FORM_268B
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
        rolled_objects = PrescribedBurn.objects.filter(date=today, rolled=True).exclude(form_name=PrescribedBurn.FORM_268A) #.exclude(completed=True)
        unset_objects = list(set(rolled_objects.filter(area__isnull=True)).union(rolled_objects.filter(status__isnull=True)))
        return unset_objects

    def export_to_csv(self, request, extra_context=None):
        if request.GET.has_key('toDate') and request.GET.has_key('fromDate'):
            fromDate = datetime.strptime(request.GET.get('fromDate'), '%Y-%m-%d').date()
            toDate = datetime.strptime(request.GET.get('toDate'), '%Y-%m-%d').date()
            burns = PrescribedBurn.objects.filter(date__range=[fromDate, toDate])
            filename = 'export_daily_burn_program_{0}-{1}.csv'.format(fromDate.strftime('%d%b%Y'), toDate.strftime('%d%b%Y'))
        elif request.GET.has_key('date'):
            report_date = datetime.strptime(request.GET.get('date'), '%Y-%m-%d').date()
            burns = PrescribedBurn.objects.filter(date=report_date)
            filename = 'export_daily_burn_program_{0}.csv'.format(report_date.strftime('%d%b%Y'))
        else:
            raise Http404('Could not get Date')

        query_list = []
        id_list = []

        for pb in burns:
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

            form_name = pb.get_form_name_display().strip('Form ')
            fire_type = pb.fire_type
            dt = pb.date.strftime('%Y-%m-%d')
            burn_status = pb.get_status_display()
            ignition_status = pb.get_ignition_status_display()
            external_assist = ', '.join([i.name for i in pb.external_assist.all()])
            planned_area = pb.planned_area
            area = pb.area
            tenures = pb.tenures
            location = pb.location
            est_start = pb.est_start
            conditions = pb.conditions

            user_acknow_formA = pb.user_a_record
            srm_acknow_formA = pb.srm_a_record
            sdo_acknow_formA = pb.sdo_a_record
            user_acknow_formB = pb.user_b_record
            srm_acknow_formB = pb.srm_b_record
            sdo_acknow_formB = pb.sdo_b_record
            rolled = "Yes" if pb.rolled else ""

            query_list.append([fire_id, name, region, district, fire_type, form_name,
                               dt, burn_status, ignition_status, external_assist,
                               planned_area, area, tenures, location, est_start, conditions,
                               user_acknow_formA, srm_acknow_formA, sdo_acknow_formA,
                               user_acknow_formB, srm_acknow_formB, sdo_acknow_formB,
                               rolled])

        response = HttpResponse(content_type="text/csv")
        response['Content-Disposition'] = 'attachment; filename={}'.format(filename)

        writer = unicodecsv.writer(response, quoting=unicodecsv.QUOTE_ALL)

        writer.writerow(["Fire ID", "Name", "Region", "District", "Type", "Form",
            "Date", "Burn Status", "Ignition Status", "Assistance received from",
            "Planned Area", "Actual Area", "Tenures", "Location", "Est Start", "Conditions",
            "DDO Acknow FormA", "RDO Acknow FormA", "SDO Acknow FormA",
            "DDO Acknow FormB", "RDO Acknow FormB", "SDO Acknow FormB",
            "Rolled"])

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
            prescribed_burns = prescribed_burns.filter(region=region)
            region_name = Region.objects.get(id=int(region)).name
        else:
            region = None
            region_name = "Statewide"


        planned_burns = prescribed_burns.filter(form_name=PrescribedBurn.FORM_268A, acknowledgements__acknow_type__in=['SDO_A']).exclude(prescription__isnull=True)
        fireload = prescribed_burns.filter(form_name=PrescribedBurn.FORM_268B, status=PrescribedBurn.BURN_ACTIVE, acknowledgements__acknow_type__in=['SDO_B'])

        planned_burns_rdo = prescribed_burns.filter(form_name=PrescribedBurn.FORM_268A, acknowledgements__acknow_type__in=['SRM_A']).exclude(prescription__isnull=True)
        fireload_rdo = prescribed_burns.filter(form_name=PrescribedBurn.FORM_268B, status=PrescribedBurn.BURN_ACTIVE, acknowledgements__acknow_type__in=['SRM_B'])

        def acknow(burns, acknow_type):
            acknowledgements = Acknowledgement.objects.filter(burn__in=burns, acknow_type=acknow_type).distinct()
            return ', '.join(set([i.user.get_full_name() for i in acknowledgements]))

        acknow_records ={
            'srm_A': acknow(planned_burns, 'SRM_A'),
            'sdo_A': acknow(planned_burns, 'SDO_A'),
            'srm_B': acknow(fireload, 'SRM_B'),
            'sdo_B': acknow(fireload, 'SDO_B')
        }
        obj = Prescription.objects.get(id=620)
        template = request.GET.get("template", "pfp")
        response = HttpResponse(content_type='application/pdf')
        #texname = template + ".tex"
        #filename = template + ".pdf"
        texname = template + "_" + request.user.username + ".tex"
        filename = template + "_" + request.user.username + ".pdf"
        now = timezone.localtime(timezone.now())
        timestamp = now.isoformat().rsplit(
            ".")[0].replace(":", "")
        downloadname = "daily_burn_program"
        error_response = HttpResponse(content_type='text/html')
        errortxt = downloadname.replace(".pdf", ".errors.txt.html")
        error_response['Content-Disposition'] = (
            '{0}; filename="{1}"'.format(
            "inline", errortxt))

        subtitles = {
            #"daily_burn_program": "Part A - Daily Burn Program",
            "form268a": "268a - Planned Burns",
            "form268a_rdo": "268a - Planned Burns (RDO ONLY)",
            "form268b": "268b - Fire Load",
            "form268b_rdo": "268b - Fire Load (RDO ONLY)",
            "form268c": "268c - Approved Burns",
        }
        embed = False if request.GET.get("embed") == "false" else True
        context = {
            'user': request.user.get_full_name(),
            'date': datetime.now().strftime('%d %b %Y'),
            'region': region_name,
            'time': datetime.now().strftime('%H:%M'),
            'report_date': report_date.strftime('%d %b %Y'),
            'state_regional_manager': datetime.now().strftime('%H:%M'),
            'qs_planned_burns': planned_burns.order_by('prescription__burn_id'),
            'qs_fireload': fireload.order_by('prescription__burn_id'),
            'qs_planned_burns_rdo': planned_burns_rdo.order_by('prescription__burn_id'),
            'qs_fireload_rdo': fireload_rdo.order_by('prescription__burn_id'),
            'acknow_records': acknow_records,
            'active_records': self.active_records(report_date, region),
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
        disposition = "attachment"
        response['Content-Disposition'] = (
            '{0}; filename="{1}"'.format(
                disposition, downloadname))

        directory = os.path.join(settings.MEDIA_ROOT, 'daily-burn-program' + os.sep)
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

        with open(directory + texname, "w") as f:
            f.write(output.encode('utf-8'))
            logger.debug("Writing to {}".format(directory + texname))

        logger.debug("Starting PDF rendering process ...")
        cmd = ['latexmk', '-cd', '-f', '-silent', '-pdf', directory + texname]
        logger.debug("Running: {0}".format(" ".join(cmd)))
        subprocess.call(cmd)

        logger.debug("Cleaning up ...")
        cmd = ['latexmk', '-cd', '-c', directory + texname]
        logger.debug("Running: {0}".format(" ".join(cmd)))
        subprocess.call(cmd)

        logger.debug("Reading PDF output from {}".format(filename))
        response.write(open(directory + filename).read())
        logger.debug("Finally: returning PDF response.")
        return response





