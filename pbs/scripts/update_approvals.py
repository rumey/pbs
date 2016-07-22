import os
import sys
import confy
from django.core.wsgi import get_wsgi_application
try:
    confy.read_environment_file('.env')
except:
    print('ERROR: Script must be runs from PROJECT BASE_DIR')
    exit()

application = get_wsgi_application() # This is so models get loaded.

proj_path = os.getcwd()
sys.path.append(proj_path)
os.chdir(proj_path)

# ----------------------------------------------------------------------------------------
# Script starts here
# ----------------------------------------------------------------------------------------

import csv
from datetime import datetime, date
import pytz
from pbs.prescription.models import Prescription

def read_ids(filename):
    return [i[0] for i in list(csv.reader(open(filename), delimiter=',', quotechar='"'))]

def update_currently_approved(ids):
    count = 0
    for p in Prescription.objects.filter(burn_id__in=ids):
        p.financial_year = '2016/2017'
        p.planning_status_modified = datetime(2016, 6, 27, tzinfo=pytz.UTC)
        p.save()
        count += 1
    print 'Updated Currently Approved season and approved date for {} ePFPs'.format(count)

def update_seeking_approval(ids):
    count = 0
    for p in Prescription.objects.filter(burn_id__in=ids):
        p.planning_status = 3
        p.planning_status_modified = datetime(2016, 6, 27, tzinfo=pytz.UTC)
        p.save()
        count += 1
    print 'Updated Seeking Approval status from DRAFT to APPROVED and Approval Date for {} ePFPs'.format(count)

def update_season(ids):
    count = 0
    for p in Prescription.objects.filter(burn_id__in=ids):
        p.financial_year = '2016/2017'
        p.save()
        count += 1
    print 'Updated Seeking Approval status from DRAFT to APPROVED for {} ePFPs'.format(count)

def update_seeking_approval_2(ids):
    count = 0
    for p in Prescription.objects.filter(burn_id__in=ids):
        p.planning_status = 3                                                   # corporate approved
        p.financial_year = '2016/2017'                                          # SEASON
        p.planning_status_modified = datetime(2016, 7, 01, tzinfo=pytz.UTC)     # approval date
        a=p.approval_set.all()
        if len(a) > 0:
            a[0].valid_to=date(2016, 7, 15)                                     # approved until date
            a[0].save()
        p.save()
        count += 1
    print 'Updated Seeking Approval status from DRAFT to APPROVED and Approval Date for {} ePFPs'.format(count)

def print_burnstate_reviewed(ids):
    count = 0
    for p in Prescription.objects.filter(burn_id__in=ids).order_by('burn_id'):
        if p.burnstate.all(): # and not reviewable(p):
            print p.burn_id, ';', [i.record for i in p.burnstate.all()], ';', reviewable(p)

def delete_burnstate_unreviewed(ids):
    count = 0
    for p in Prescription.objects.filter(burn_id__in=ids).order_by('burn_id'):
        if p.burnstate.all() and not reviewable(p):
            b = p.burnstate.all()
            b.delete()

def reviewable(prescription):
    p = Prescription.objects.filter(
            id=prescription.id,
            approval_status=Prescription.APPROVAL_APPROVED,
            status=Prescription.STATUS_OPEN,
            ignition_status__in=[Prescription.IGNITION_NOT_STARTED, Prescription.IGNITION_COMMENCED]
        )
    return True if p else False

if __name__ == "__main__":
#    cur_approved_ids = read_ids('pbs/scripts/currently_approved.txt')
#    update_currently_approved(cur_approved_ids)
    #print cur_approved_ids, len(cur_approved_ids)

#    seeking_approval_ids = read_ids('pbs/scripts/seeking_approval.txt')
#    update_seeking_approval(seeking_approval_ids)

#    update_season_ids = read_ids('pbs/scripts/update_season.txt')
#    update_season(update_season_ids)

#    seeking_approval_ids = read_ids('pbs/scripts/seeking_approval-2.txt')
#    #print seeking_approval_ids, len(seeking_approval_ids)
#    update_seeking_approval_2(seeking_approval_ids)

    ids = read_ids('pbs/scripts/seeking_approval_reviewed.txt')
    #print_burnstate_reviewed(ids)

    delete_burnstate_unreviewed(ids)
    #ids = read_ids('pbs/scripts/seeking_approval_reviewed.txt')
    print_burnstate_reviewed(ids)
