from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from django.conf import settings
from django.db import transaction
import os
import sys 

from pbs.prescription.models import (EndorsingRole,Prescription,Endorsement)

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = """
Manage endorsement roles 
"""
    option_list = BaseCommand.option_list + (
        make_option('--list',
            action='store_const',
            const="list",
            dest='action',
            help='List all endorsement roles'),
        make_option('--detail',
            action='store_const',
            const="detail",
            dest='action',
            help='Show role detail information, including role profile, prescription which require this role to endorse and whether it is endorsed or not '),
        make_option('--archive',
            action='store_const',
            const="archive",
            dest='action',
            help='Archive this role, set role.archived=True; Remove all role endorse requirement if it is not endorsed; keep all role endorse requirement and its status if it is endorsed;'),
        make_option('--force',
            action='store_true',
            dest='force',
            default=False,
            help='If action is achive, all role related endorsement which is not endorsed will be removed, including the "Reviewed and refused" endorsement.'),
        make_option('--role_id',
            action='store',
            type="int",
            dest='role_id',
            help='The role id'),
        )

    def endorsement_status_name(self,endorsement_status):
        for choice in Prescription.ENDORSEMENT_CHOICES:
            if choice[0] == endorsement_status:
                return choice[1]

        return "Unknown"

    def handle(self, *args, **options):
        if options.get("role_id") is not None:
            options["action"] = options.get("action") or "detail"
        else:
            options["action"] = options.get("action") or "list"

        if options["action"] in ["detail","archive"]:
            if not options.get("role_id"):
                raise Exception("Role id required.")
            try:
                role = EndorsingRole.objects.get(id=options["role_id"])
            except EndorsingRole.DoesNotExist:
                raise Exception("Role ({}) does not exist".format(options["role_id"]))
            print("id={0: <3}\tname={3: <64}\tindex={1: <3}\tarchived={2: <6}".format(role.id,role.index,"Yes" if role.archived else "No" ,role.name))

            warning_pres = []
            removed_pres = []
            endorsed_pres = []
            reserved_pres = []

            with transaction.atomic():
                if options["action"] == "archive" and not role.archived:
                    role.archived = True
                    role.save()
                for pre in Prescription.objects.filter(endorsing_roles__id__exact = role.id):
                    try:
                        endorsement = Endorsement.objects.get(prescription=pre,role=role)
                    except Endorsement.DoesNotExist:
                        endorsement = None
                    if endorsement and endorsement.endorsed:
                        reserved_pres.append((pre,endorsement))
                    elif endorsement and not options["force"]:
                        warning_pres.append((pre,endorsement))
                    elif pre.endorsement_status == Prescription.ENDORSEMENT_APPROVED and not options["force"]:
                        warning_pres.append((pre,endorsement)) 
                    else:
                        if options["action"] == "archive":
                            if endorsement:
                                endorsement.delete()
                            pre.endorsing_roles.remove(role)
                            if pre.endorsement_status == Prescription.ENDORSEMENT_SUBMITTED and pre.all_endorsed:
                                pre.endorsement_status = Prescription.ENDORSEMENT_APPROVED
                                pre.save()

                        if pre.endorsement_status == Prescription.ENDORSEMENT_SUBMITTED and pre.all_endorsed:
                            endorsed_pres.append((pre,endorsement))
                        else:
                            removed_pres.append((pre,endorsement))

            for t,pres in [
                    ("are reserved" if options["action"] == "archive" else " will be reserved.",reserved_pres),
                    ("are removed" if options["action"] == "archive" else " will be removed.",removed_pres),
                    ("are removed and related ePFPs are endorsed automatically" if options["action"] == "archive" else " will be removed and related ePFPs will be endorsed automatically.",endorsed_pres),
                    (" can't processed automatically and require user double check, can be processed by adding option '--force'.",warning_pres)]:
                if len(pres) == 0:
                    continue
                print("===============================================================================================")
                print("The following {} role endorsement data {}".format(len(pres),t))
                for pre,endorsement in pres:
                    print("\tid={0: <10} name={1: <90} endorsement_status={2: <32} role_endorsement_status={3: <8}".format(pre.id,pre.name[0:90],self.endorsement_status_name(pre.endorsement_status),"Yes" if endorsement and endorsement.endorsed else ("Reviewed" if endorsement else "No")))
        else:
            for role in EndorsingRole.objects.all().order_by("name"):
                print("id={0: <3}\tname={3: <64}\tindex={1: <3}\tarchived={2: <6}".format(role.id,role.index,"Yes" if role.archived else "No" ,role.name))

        pass;

