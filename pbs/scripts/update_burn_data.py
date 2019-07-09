import os
import sys
import confy
from django.core.wsgi import get_wsgi_application
from decimal import Decimal

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

def read_ids_pipe_separated(filename):
    return [i[0] for i in list(csv.reader(open(filename), delimiter='|', quotechar='"'))]

def read_id_tuples(filename):
    return [tuple(i) for i in list(csv.reader(open(filename), delimiter=',', quotechar='"'))]

def read_id_tuples_pipe_separated(filename):
    return [tuple(i) for i in list(csv.reader(open(filename), delimiter='|', quotechar='"'))]

def carryover_currently_approved(ids):
    # Used to update the financial year of existing corporate approved ePFPs from previous year
    # Also updates the date modified of the Planning Status (approval date)
    print('\nUpdating financial year and setting planning status modified date for carry over currently approved ePFPs from 2017/2018.')
    count = 0
    for p in Prescription.objects.filter(burn_id__in=ids):
        if (p.financial_year != '2017/2018'):
            print('Financial year for {}({}) is not 2017/2018.'.format(str(p.burn_id),p.financial_year))
        else:
            if (p.planning_status != 3): # only apply if corporate approved
                print('Planning status for {} is not currently corporate approved.'.format(str(p.burn_id)))
            else:
                if (p.status != 2): # burn status must not be closed
                    p.financial_year = '2018/2019'
                    p.planning_status_modified = datetime(2018, 7, 2, tzinfo=pytz.UTC)
                    p.save()
                    count += 1
                else:
                    print('Burn status for {} is closed'.format(str(p.burn_id)))
    print('Updated financial year and set planning status modified date for {} carry over currently approved ePFPs'.format(count))

def update_seeking_approval(ids):
    # Used to apply corporate approval to ePFPs (usually for list of ePFPs currently seeking approval)
    # Also updates the date modified of the Planning Status (approval date)
    print('\nApplying corporate approval and setting planning status modified date for ePFPs currently seeking approval in 2018/2019.')
    count = 0
    for p in Prescription.objects.filter(burn_id__in=ids):
        if (p.financial_year != '2018/2019'):
            print('Financial year for {}({}) is not 2018/2019.'.format(str(p.burn_id),p.financial_year))
        else:
            if (p.planning_status != 2): # only apply if seeking corporate approval 
                print('Planning status for {} is not currently seeking corporate approval.'.format(str(p.burn_id)))
            else:
                if (p.status != 2): # burn status must not be closed
                    p.planning_status = 3 # corporate approved
                    p.planning_status_modified = datetime(2018, 7, 2, tzinfo=pytz.UTC)
                    p.save()
                    count += 1
                else:
                    print('Burn status for {} is closed'.format(str(p.burn_id)))
    print('Applied corporate approval and set planning status modified date for {} ePFPs that were seeking approval'.format(count))

def update_financial_year(ids):
    # Used to update the financial year of existing ePFPs from previous year
    print('\nUpdating financial year only selected ePFPs from 2017/2018')
    count = 0
    for p in Prescription.objects.filter(burn_id__in=ids):
        if (p.financial_year != '2017/2018'):
            print('Financial year for {}({}) is not 2017/2018.'.format(str(p.burn_id),p.financial_year))
        else:
            p.financial_year = '2018/2019'
            p.save()
            count += 1
    print('Updated financial year only for {} ePFPs'.format(count))

def update_seeking_approval_2(ids):
    # Used to apply corporate approval to ePFPs (usually for list of ePFPs currently seeking approval) from previous year
    # Also updates the date modified of the Planning Status (approval date)
    # and updates the valid_to date of an existing approval to enable access to the ePFP
    # as part of the Daily Burn Progrm 268 process
    print('\nApplying corporate approval and setting planning status modified date for ePFPs currently seeking approval in 2018/2019.')
    print('Also set valid_to date for approval for Daily Burn Program access')
    count = 0
    for p in Prescription.objects.filter(burn_id__in=ids):
        if (p.financial_year != '2018/2019'):
            print('Financial year for {}({}) is not 2018/2019.'.format(str(p.burn_id),p.financial_year))
        else:
            if (p.planning_status != 2): # only apply if seeking corporate approval 
                print('Planning status for {} is not currently seeking corporate approval.'.format(str(p.burn_id)))
            else:
                if (p.status != 2): # burn status must not be closed
                    p.planning_status = 3                                                   # corporate approved
                    p.financial_year = '2018/2019'                                          # SEASON
                    p.planning_status_modified = datetime(2018, 7, 2, tzinfo=pytz.UTC)      # approval date
                    a=p.approval_set.all()
                    if len(a) > 0:
                        a[0].valid_to=date(2018, 9, 30)                                     # approved until date
                        a[0].save()
                    p.save()
                    count += 1
                else:
                    print('Burn status for {} is closed'.format(str(p.burn_id)))
    print('Applied corporate approval and set planning status modified date for {} ePFPs that were seeking approval'.format(count))

def update_burn_priority(id_priority_pairs):
    # Used to update the priority of the listed ePFPs
    print('\nUpdating priority for selected ePFPs in 2018/2019')
    count = 0
    for burn_id, priority in id_priority_pairs:
        for p in Prescription.objects.filter(burn_id=burn_id):
            if (p.financial_year != '2018/2019'):
                print('Financial year for {}({}) is not 2018/2019.'.format(str(p.burn_id),p.financial_year))
            else:
                p.priority = int(priority)
                p.save()
                count += 1
    print 'Updated priority for {} ePFPs'.format(count)

def update_burn_areas(id_burn_area_pairs):
    # Used to update the area of the listed ePFPs
    print('\nUpdating area for selected ePFPs in 2018/2019')
    count = 0
    for burn_id, area in id_burn_area_pairs:
        for p in Prescription.objects.filter(burn_id=burn_id):
            if (p.financial_year != '2018/2019'):
                print('Financial year for {}({}) is not 2018/2019.'.format(str(p.burn_id),p.financial_year))
            else:
                p.area = Decimal(area)
                p.save()
                count += 1
    print 'Updated area for {} ePFPs'.format(count)

def update_burn_perimeters(id_perimeter_pairs):
    # Used to update the perimeters of the listed ePFPs
    print('\nUpdating perimeters for selected ePFPs in 2018/2019')
    count = 0
    for burn_id, perimeter in id_perimeter_pairs:
        for p in Prescription.objects.filter(burn_id=burn_id):
            if (p.financial_year != '2018/2019'):
                print('Financial year for {}({}) is not 2018/2019.'.format(str(p.burn_id),p.financial_year))
            else:
                p.perimeter = Decimal(perimeter)
                p.save()
                count += 1
    print 'Updated perimeter for {} ePFPs'.format(count)

def update_overall_rationales(id_overall_rationale_pairs):
    # Used to update the overall rationale of the listed ePFPs
    print('\nUpdating overall rationale for selected ePFPs in 2018/2019')
    count = 0
    for burn_id, rationale in id_overall_rationale_pairs:
        for p in Prescription.objects.filter(burn_id=burn_id):
            if (p.financial_year != '2018/2019'):
                print('Financial year for {}({}) is not 2018/2019.'.format(str(p.burn_id),p.financial_year))
            else:
                p.rationale = rationale
                p.save()
                count += 1
    print 'Updated rationale for {} ePFPs'.format(count)

def print_burnstate_reviewed(ids):
    count = 0
    for p in Prescription.objects.filter(burn_id__in=ids,financial_year='2018/2019').order_by('burn_id'):
        if p.burnstate.all(): # and not reviewable(p):
            print p.burn_id, ';', [i.record for i in p.burnstate.all()], ';', reviewable(p)

def delete_burnstate_unreviewed(ids):
    count = 0
    for p in Prescription.objects.filter(burn_id__in=ids,financial_year='2018/2019').order_by('burn_id'):
        if p.burnstate.all() and not reviewable(p):
            b = p.burnstate.all()
            b.delete()

def reviewable(prescription):
    p = Prescription.objects.filter(
            id=prescription.id,
            approval_status=Prescription.APPROVAL_APPROVED,
            status=Prescription.STATUS_OPEN,
            ignition_status__in=[Prescription.IGNITION_NOT_STARTED, Prescription.IGNITION_COMMENCED],
            financial_year='2018/2019'
        )
    return True if p else False

if __name__ == "__main__":
    corp_approved_carryover_ids = read_ids('pbs/scripts/eofy_data/2018/corp_approved_carryover.txt')
    carryover_currently_approved(corp_approved_carryover_ids)

    seeking_approval_ids = read_ids('pbs/scripts/eofy_data/2018/approve_seeking_approval.txt')
    update_seeking_approval(seeking_approval_ids)

    update_financial_year_ids = read_ids('pbs/scripts/eofy_data/2018/financial_year_only.txt')
    update_financial_year(update_financial_year_ids)

    burn_priority_tuples = read_id_tuples('pbs/scripts/eofy_data/2018/burn_priority.txt')
    update_burn_priority(burn_priority_tuples)

    burn_area_tuples = read_id_tuples('pbs/scripts/eofy_data/2018/burn_areas.txt')
    update_burn_areas(burn_area_tuples)

    burn_perimeter_tuples = read_id_tuples('pbs/scripts/eofy_data/2018/burn_perimeters.txt')
    update_burn_perimeters(burn_perimeter_tuples)

    overall_rationale_tuples = read_id_tuples_pipe_separated('pbs/scripts/eofy_data/2018/overall_rationales.txt')
    update_overall_rationales(overall_rationale_tuples)

#    seeking_approval_ids = read_ids('pbs/scripts/seeking_approval-2.txt')
#    #print seeking_approval_ids, len(seeking_approval_ids)
#    update_seeking_approval_2(seeking_approval_ids)

    #print_burnstate_reviewed(ids)

    #delete_burnstate_unreviewed(ids)
    #ids = read_ids('pbs/scripts/seeking_approval_reviewed.txt')
    #print_burnstate_reviewed(ids)
