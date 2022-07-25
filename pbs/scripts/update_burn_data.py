''' ----------------------------------------------------------------------------------------
This script will update the Prescribed Burn System's ePFP data according to txt input
files found in the relevant scripts folder.
It requires user input of the Corporate Executive Approval date, which it will then use
to set PREVIOUS_YEAR, TARGET_YEAR, DATE_APPROVED and DATE_APPROVED_TO variables used by
relevant functions in the script.

Sample output below:

    Please enter the date that the Burn Program was approved by Corporate Executive (dd/mm/yyyy): 03/07/2019
    Script will run with the following details:
     - Previous Year: 2018/2019
     - Target Year: 2019/2020
     - Script Data Folder: pbs/scripts/eofy_data/2019

    Do you wish to continue [y/n]? y

    Updating financial year and setting planning status modified date for carry over currently approved ePFPs from 2018/2019.
    Total prescriptions in query: 331
    Financial year for ABC_123(2013/2014) is not 2018/2019 or already in 2019/2020.
    Updated financial year and set planning status modified date for 330 carry over currently approved ePFPs

    Applying corporate approval and setting planning status modified date for ePFPs currently seeking approval in 2019/2020.
    Total prescriptions in query: 51
    Applied corporate approval and set planning status modified date for 51 ePFPs that were seeking approval

    Updating financial year only selected ePFPs from 2018/2019
    Total prescriptions in query: 330
    Financial year for ABC_123(2013/2014) is not 2018/2019.
    Updated financial year only for 0 ePFPs
    329 records already in 2019/2020

    Updating priority for selected ePFPs in 2019/2020
    Financial year for ABC_123(2013/2014) is not 2019/2020.
    Updated priority for 412 ePFPs (expected 412)

    Updating area for selected ePFPs in 2019/2020
    Financial year for ABC_123(2013/2014) is not 2019/2020.
    Updated area for 412 ePFPs (expected 412)

    Updating perimeters for selected ePFPs in 2019/2020
    Financial year for ABC_123(2013/2014) is not 2019/2020.
    Updated perimeter for 412 ePFPs (expected 412)

    Updating overall rationale for selected ePFPs in 2019/2020
    Financial year for ABC_123(2013/2014) is not 2019/2020.
    Updated rationale for 168 ePFPs (expected 168)

----------------------------------------------------------------------------------------
'''
import os
import sys
#import confy
from django.db import transaction
from django.core.wsgi import get_wsgi_application
from decimal import Decimal
import csv
from datetime import datetime, date
import pytz

application = get_wsgi_application()  # This is so models get loaded.

#try:
#   confy.read_environment_file('.env')
#except:
#    print('ERROR: Script must be runs from PROJECT BASE_DIR')
#    exit()

if not (os.path.isdir('pbs') and os.path.isdir('pbs_project')):
    print('ERROR: Script must be run from PROJECT BASE_DIR')
    exit()

proj_path = os.getcwd()
sys.path.append(proj_path)
os.chdir(proj_path)

# ----------------------------------------------------------------------------------------
# Script starts here
# ----------------------------------------------------------------------------------------

from pbs.prescription.models import Prescription

report_text = []

def read_ids(filename):
    return [i[0].strip() for i in list(csv.reader(open(filename), delimiter=',', quotechar='"'))]


def read_ids_pipe_separated(filename):
    return [i[0] for i in list(csv.reader(open(filename), delimiter='|', quotechar='"'))]


def read_id_tuples(filename):
    return [tuple(i) for i in list(csv.reader(open(filename), delimiter=',', quotechar='"'))]


def read_id_tuples_pipe_separated(filename):
    return [tuple(i) for i in list(csv.reader(open(filename), delimiter='|', quotechar='"'))]


def carryover_currently_approved(ids):
    # Used to update the financial year of existing corporate approved ePFPs from previous year
    # Also updates the date modified of the Planning Status (approval date)
    report_text.append('\nUpdating financial year and setting planning status '
          'modified date for carry over currently approved ePFPs from {}.'.format(PREVIOUS_YEAR))
    updated_count = 0
    burn_count = 0
    input_data_count = len([burn_id for burn_id in ids if burn_id != ""])
    for p in Prescription.objects.filter(burn_id__in=ids).order_by('burn_id'):
        # Only update if the ePFP is in PREVIOUS_YEAR or if it has already been changed to TARGET_YEAR
        # and no remaining records for PREVIOUS_YEAR exist
        if (p.financial_year == PREVIOUS_YEAR or
                (p.financial_year == TARGET_YEAR and
                 Prescription.objects.filter(burn_id=p.burn_id, financial_year=PREVIOUS_YEAR).count() == 0)):
            if p.planning_status != 3:  # only apply if corporate approved
                report_text.append('Planning status for {} is not currently corporate approved.'.format(str(p.burn_id)))
            else:
                if p.status != 2:  # burn status must not be closed
                    p.financial_year = TARGET_YEAR
                    p.planning_status_modified = DATE_APPROVED
                    p.save()
                    updated_count += 1
                else:
                    report_text.append('Burn status for {} is closed'.format(str(p.burn_id)))
        else:
            report_text.append('Financial year for {}({}) is not {} or already in {}.'
                  .format(str(p.burn_id), p.financial_year, PREVIOUS_YEAR, TARGET_YEAR))
        burn_count += 1
    report_text.append('Updated financial year and set planning status modified date for {} carry over currently approved ePFPs; expected {} and rejected {}.'.format(updated_count, input_data_count, burn_count - updated_count))

def carryover_without_approvals(ids):
    # Used to update the financial year of existing corporate approved ePFPs from previous year
    # Also updates the date modified of the Planning Status (approval date)
    report_text.append('\nUpdating financial year and removing endorsements and approvals from burns on {} program.'.format(PREVIOUS_YEAR))
    updated_count = 0
    burn_count = 0
    input_data_count = len([burn_id for burn_id in ids if burn_id != ""])
    for p in Prescription.objects.filter(burn_id__in=ids).order_by('burn_id'):
        # Only update if the ePFP is in PREVIOUS_YEAR or if it has already been changed to TARGET_YEAR
        # and no remaining records for PREVIOUS_YEAR exist
        if (p.financial_year == PREVIOUS_YEAR or
                (p.financial_year == TARGET_YEAR and
                 Prescription.objects.filter(burn_id=p.burn_id, financial_year=PREVIOUS_YEAR).count() == 0)):
            if p.planning_status != 3:  # only apply if corporate approved
                report_text.append('Planning status for {} is not currently corporate approved.'.format(str(p.burn_id)))
            else:
                if p.status != 2:  # burn status must not be closed
                    p.financial_year = TARGET_YEAR
                    #p.endorsement_status = 1
                    p.clear_approvals()
                    p.endorsement_status_modified = DATE_APPROVED
                    #p.approval_status = 1
                    p.approval_status_modified = DATE_APPROVED
                    p.planning_status_modified = DATE_APPROVED
                    p.save()
                    report_text.append(p.burn_id + " done")
                    updated_count += 1
                else:
                    report_text.append('Burn status for {} is closed'.format(str(p.burn_id)))
        else:
            report_text.append('Financial year for {}({}) is not {} or already in {}.'.format(str(p.burn_id), p.financial_year, PREVIOUS_YEAR, TARGET_YEAR))
        burn_count += 1
    report_text.append('Updated financial year and removed endorsements and approvals for {} burns; expected {} and rejected {}.'.format(updated_count, input_data_count, burn_count - updated_count))

def update_seeking_approval(ids):
    # Used to apply corporate approval to ePFPs (usually for list of ePFPs currently seeking approval)
    # Also updates the date modified of the Planning Status (approval date)
    report_text.append('\nApplying corporate approval and setting planning status'
          ' modified date for ePFPs currently seeking approval in {}.'.format(TARGET_YEAR))
    updated_count = 0
    burn_count = 0
    input_data_count = len([burn_id for burn_id in ids if burn_id != ""])
    for p in Prescription.objects.filter(burn_id__in=ids).order_by('burn_id'):
        # Only update if the ePFP is in PREVIOUS_YEAR or if it has already been changed to TARGET_YEAR
        # and no remaining records for PREVIOUS_YEAR exist
        if (p.financial_year == PREVIOUS_YEAR or
                (p.financial_year == TARGET_YEAR and
                 Prescription.objects.filter(burn_id=p.burn_id, financial_year=PREVIOUS_YEAR).count() == 0)):
            if p.planning_status != 2:  # only apply if seeking corporate approval
                report_text.append('Planning status for {} is not currently seeking corporate approval.'.format(str(p.burn_id)))
            else:
                if p.status != 2:  # burn status must not be closed
                    p.financial_year = TARGET_YEAR
                    p.planning_status = 3  # corporate approved
                    p.planning_status_modified = DATE_APPROVED
                    p.save()
                    updated_count += 1
                else:
                    report_text.append('Burn status for {} is closed'.format(str(p.burn_id)))
        else:
            report_text.append('Financial year for {}({}) is not {} or already in {}.'.format(str(p.burn_id), p.financial_year, PREVIOUS_YEAR, TARGET_YEAR))
        burn_count += 1
    report_text.append('Applied corporate approval and set planning status modified date for {} ePFPs that were seeking approval; expected {} and rejected {}.'.format(updated_count, input_data_count, burn_count - updated_count))

def apply_corp_approval(ids):
    # Used to apply corporate approval to ePFPs for current year, which have not come 
    # under 'seeking corporate approval'.
    # Also updates the date modified of the Planning Status (approval date)
    report_text.append('\nApplying corporate approval and setting planning status modified date' 
         'for ePFPs for {} '.format(TARGET_YEAR))
    report_text.append('Also set valid_to date for approval for Daily Burn Program access')
    count = 0
    report_text.append('Total prescriptions in query: {}'.format(Prescription.objects.filter(burn_id__in=ids).count()))
    for p in Prescription.objects.filter(burn_id__in=ids).order_by('burn_id'):
        if p.financial_year != TARGET_YEAR:
            report_text.append('Financial year for {}({}) is not {}.'.format(str(p.burn_id), p.financial_year, TARGET_YEAR))
        else:
            #if p.planning_status == 2:  # do not apply if seeking corporate approval
            #    report_text.append('Planning status for {} is currently seeking corporate approval.'.format(str(p.burn_id)))
            if p.planning_status == 3:  # do not apply if already has corporate approval
                report_text.append('Planning status for {} is already set to  corporate approved.'.format(str(p.burn_id)))
            else:
                if p.status != 2:  # burn status must not be closed
                    p.planning_status = 3                       # corporate approved
                    p.financial_year = TARGET_YEAR              # season
                    p.planning_status_modified = DATE_APPROVED  # approval date
                    a = p.approval_set.all()
                    if len(a) > 0:
                        a[0].valid_to = DATE_APPROVED_TO        # approved until date
                        a[0].save()
                    p.save()
                    count += 1
                else:
                    report_text.append('Burn status for {} is closed'.format(str(p.burn_id)))
    report_text.append('Applied corporate approval and set planning status modified date '
          'for {} ePFPs'.format(count))

def update_financial_year(ids):
    # Used to update the financial year of existing ePFPs from previous year
    report_text.append('\nUpdating financial year only selected ePFPs from {}'.format(PREVIOUS_YEAR))
    already_in_target_year = 0
    updated_count = 0
    burn_count = 0
    input_data_count = len([burn_id for burn_id in ids if burn_id != ""])
    for p in Prescription.objects.filter(burn_id__in=ids).order_by('burn_id'):
        if p.financial_year != PREVIOUS_YEAR:
            if p.financial_year == TARGET_YEAR:
                already_in_target_year += 1
            else:
                report_text.append('Financial year for {}({}) is not {}.'.format(str(p.burn_id), p.financial_year, PREVIOUS_YEAR))
        else:
            p.financial_year = TARGET_YEAR
            p.save()
            updated_count += 1
        burn_count += 1
    #report_text.append('Updated financial year only for {} ePFPs'.format(count))
    #report_text.append('{} records already in {}'.format(already_in_target_year, TARGET_YEAR))
    report_text.append('Updated financial year only for {} ePFPs; expected {} and rejected {}.'.format(updated_count, input_data_count, burn_count - updated_count))

"""def update_seeking_approval_2(ids):
    # Used to apply corporate approval to ePFPs (usually for list of ePFPs currently seeking approval)
    # from previous year
    # Also updates the date modified of the Planning Status (approval date)
    # and updates the valid_to date of an existing approval to enable access to the ePFP
    # as part of the Daily Burn Program 268 process
    report_text.append('\nApplying corporate approval and setting planning status modified date '
          'for ePFPs currently seeking approval in {}.'.format(TARGET_YEAR))
    report_text.append('Also set valid_to date for approval for Daily Burn Program access')
    count = 0
    report_text.append('Total prescriptions in query: {}'.format(Prescription.objects.filter(burn_id__in=ids).count()))
    for p in Prescription.objects.filter(burn_id__in=ids).order_by('burn_id'):
        if p.financial_year != TARGET_YEAR:
            report_text.append('Financial year for {}({}) is not {}.'.format(str(p.burn_id), p.financial_year, TARGET_YEAR))
        else:
            if p.planning_status != 2:  # only apply if seeking corporate approval
                report_text.append('Planning status for {} is not currently seeking corporate approval.'.format(str(p.burn_id)))
            else:
                if p.status != 2:  # burn status must not be closed
                    p.planning_status = 3                       # corporate approved
                    p.financial_year = TARGET_YEAR              # season
                    p.planning_status_modified = DATE_APPROVED  # approval date
                    a = p.approval_set.all()
                    if len(a) > 0:
                        a[0].valid_to = DATE_APPROVED_TO        # approved until date
                        a[0].save()
                    p.save()
                    count += 1
                else:
                    report_text.append('Burn status for {} is closed'.format(str(p.burn_id)))
    report_text.append('Applied corporate approval and set planning status modified date '
          'for {} ePFPs that were seeking approval'.format(count))
"""

def remove_approvals(ids):
    # Copied in from remove_approvals.py then updated
    # Used to remove corporate approval from ePFPs
    report_text.append('\nClearing approvals for ePFPs currently approved for {}'.format(PREVIOUS_YEAR))
    updated_count = 0
    burn_count = 0
    input_data_count = len([burn_id for burn_id in ids if burn_id != ""])
    for p in Prescription.objects.filter(burn_id__in=ids).order_by('burn_id'):
        if p.financial_year != PREVIOUS_YEAR:
            report_text.append('Financial year for {} is not {}.'.format(str(p.burn_id), PREVIOUS_YEAR))
        else:
            if (p.status != 2): # burn status must not be closed
                p.clear_approvals()
                p.save()
                updated_count += 1
            else:
                report_text.append('Burn status for {} is closed'.format(str(p.burn_id)))
        burn_count += 1
    report_text.append('Cleared approvals for {} ePFPs; expected {} and rejected {}.'.format(updated_count, input_data_count, burn_count - updated_count))

def update_burn_priority(id_priority_pairs):
    # Used to update the priority of the listed ePFPs
    report_text.append('\nUpdating priority for selected ePFPs in {}'.format(TARGET_YEAR))
    updated_count = 0
    burn_count = 0
    input_data_count = 0
    for burn_id, priority in id_priority_pairs:
        for p in Prescription.objects.filter(burn_id=burn_id).order_by('burn_id'):
            if p.financial_year != TARGET_YEAR:
                report_text.append('Financial year for {}({}) is not {}.'.format(str(p.burn_id), p.financial_year, TARGET_YEAR))
            else:
                p.priority = int(priority)
                p.save()
                updated_count += 1
            burn_count += 1
        input_data_count += 1
    report_text.append( 'Updated priority for {} ePFPs; expected {} and rejected {}.'.format(updated_count, input_data_count, burn_count - updated_count))

def update_burn_areas(id_burn_area_pairs):
    # Used to update the area of the listed ePFPs
    report_text.append('\nUpdating area for selected ePFPs in {}'.format(TARGET_YEAR))
    updated_count = 0
    burn_count = 0
    input_data_count = 0
    for burn_id, area in id_burn_area_pairs:
        for p in Prescription.objects.filter(burn_id=burn_id).order_by('burn_id'):
            if p.financial_year != TARGET_YEAR:
                report_text.append('Financial year for {}({}) is not {}.'.format(str(p.burn_id), p.financial_year, TARGET_YEAR))
            else:
                p.area = Decimal(area)
                p.save()
                updated_count += 1
            burn_count += 1
        input_data_count += 1
    report_text.append( 'Updated area for {} ePFPs; expected {} and rejected {}.'.format(updated_count, input_data_count, burn_count - updated_count))

def update_burn_perimeters(id_perimeter_pairs):
    # Used to update the perimeters of the listed ePFPs
    report_text.append('\nUpdating perimeters for selected ePFPs in {}'.format(TARGET_YEAR))
    updated_count = 0
    burn_count = 0
    input_data_count = 0
    for burn_id, perimeter in id_perimeter_pairs:
        for p in Prescription.objects.filter(burn_id=burn_id).order_by('burn_id'):
            if p.financial_year != TARGET_YEAR:
                report_text.append('Financial year for {}({}) is not {}.'.format(str(p.burn_id), p.financial_year, TARGET_YEAR))
            else:
                p.perimeter = Decimal(perimeter)
                p.save()
                updated_count += 1
            burn_count += 1
        input_data_count += 1
    report_text.append( 'Updated perimeter for {} ePFPs; expected {} and rejected {}.'.format(updated_count, input_data_count, burn_count - updated_count))

def update_overall_rationales(id_overall_rationale_pairs):
    # Used to update the overall rationale of the listed ePFPs
    report_text.append('\nUpdating overall rationale for selected ePFPs in {}'.format(TARGET_YEAR))
    updated_count = 0
    burn_count = 0
    input_data_count = 0
    for burn_id, rationale in id_overall_rationale_pairs:
        if burn_id != "":
            for p in Prescription.objects.filter(burn_id=burn_id).order_by('burn_id'):
                if p.financial_year != TARGET_YEAR:
                    report_text.append('Financial year for {}({}) is not {}.'.format(str(p.burn_id), p.financial_year, TARGET_YEAR))
                else:
                    p.rationale = rationale
                    p.save()
                    updated_count += 1
                burn_count += 1
            input_data_count += 1
    report_text.append( 'Updated rationale for {} ePFPs; expected {} and rejected {}.'.format(updated_count, input_data_count, burn_count - updated_count))
    
def update_contentious(contentious_tuples):
    # Used to update the 'contentious' column of the listed ePFPs
    report_text.append('\nUpdating contentious for selected ePFPs in {}'.format(TARGET_YEAR))
    updated_count = 0
    burn_count = 0
    input_data_count = 0
    for burn_id, contentious in contentious_tuples:
        for p in Prescription.objects.filter(burn_id=burn_id).order_by('burn_id'):
            if p.financial_year != TARGET_YEAR:
                report_text.append('Financial year for {}({}) is not {}.'.format(str(p.burn_id), p.financial_year, TARGET_YEAR))
            elif contentious.upper() not in ["YES", "NO"]:
                report_text.append("'Contentious' for {} in {}/contentious_change.txt is not 'Yes' or 'No'".format(str(p.burn_id), SCRIPT_DATA_FOLDER))
            else:
                if contentious.upper() == "YES":
                    p.contentious = True
                elif contentious.upper() == "NO":
                    p.contentious = False
                p.save()
                updated_count += 1
            burn_count += 1
        input_data_count += 1
    report_text.append( 'Updated contentious status for {} ePFPs; expected {} and rejected {}.'.format(updated_count, input_data_count, burn_count - updated_count))
    
def update_contentious_rationales(contentious_rationale_tuples):
    # Used to update the contentious rationale of the listed ePFPs
    report_text.append('\nUpdating contentious rationale for selected ePFPs in {}'.format(TARGET_YEAR))
    updated_count = 0
    burn_count = 0
    input_data_count = 0
    for burn_id, rationale in contentious_rationale_tuples:
        if burn_id != "":
            for p in Prescription.objects.filter(burn_id=burn_id).order_by('burn_id'):
                if p.financial_year != TARGET_YEAR:
                    report_text.append('Financial year for {}({}) is not {}.'.format(str(p.burn_id), p.financial_year, TARGET_YEAR))
                else:
                    p.contentious_rationale = rationale
                    p.save()
                    updated_count += 1
                burn_count += 1
            input_data_count += 1
    report_text.append('Updated contentious rationale for {} ePFPs; expected {} and rejected {}.'.format(updated_count, input_data_count, burn_count - updated_count))

def print_burnstate_reviewed(ids):
    count = 0
    for p in Prescription.objects.filter(burn_id__in=ids, financial_year=TARGET_YEAR).order_by('burn_id'):
        if p.burnstate.all():  # and not reviewable(p):
            print p.burn_id, ';', [i.record for i in p.burnstate.all()], ';', reviewable(p)

def delete_burnstate_unreviewed(ids):
    count = 0
    for p in Prescription.objects.filter(burn_id__in=ids, financial_year=TARGET_YEAR).order_by('burn_id'):
        if p.burnstate.all() and not reviewable(p):
            b = p.burnstate.all()
            b.delete()

def reviewable(prescription):
    p = Prescription.objects.filter(
            id=prescription.id,
            approval_status=Prescription.APPROVAL_APPROVED,
            status=Prescription.STATUS_OPEN,
            ignition_status__in=[Prescription.IGNITION_NOT_STARTED, Prescription.IGNITION_COMMENCED],
            financial_year=TARGET_YEAR
        ).order_by('burn_id')
    return True if p else False

"""
if __name__ == "__main__":
    try:
        SCRIPT_FOLDER = 'pbs/scripts'
        DATE_APPROVED_INPUT = raw_input("Please enter the date that the Burn Program was approved "
                                        "by Corporate Executive (dd/mm/yyyy): ")
        DATE_APPROVED = datetime.strptime(DATE_APPROVED_INPUT, '%d/%m/%Y').replace(tzinfo=pytz.UTC)

        if DATE_APPROVED.month != 7 or DATE_APPROVED.year != date.today().year:
            print('Can only run this script in July of the current year')
            sys.exit()

        DATE_APPROVED_TO = date(DATE_APPROVED.year, 9, 30)
        PREVIOUS_YEAR = '{}/{}'.format(DATE_APPROVED.year-1, DATE_APPROVED.year)
        TARGET_YEAR = '{}/{}'.format(DATE_APPROVED.year, DATE_APPROVED.year+1)
        SCRIPT_DATA_FOLDER = '{}/eofy_data/{}'.format(SCRIPT_FOLDER, TARGET_YEAR.split('/')[0])

    except BaseException:
        print('Error')
        sys.exit()

    print('\nMain Script will run with the following details:')
    print(' - Previous Year: {}'.format(PREVIOUS_YEAR))
    print(' - Target Year: {}'.format(TARGET_YEAR))
    print(' - Script Data Folder: {}/'.format(SCRIPT_DATA_FOLDER))
    CONTINUE_INPUT = raw_input("Do you wish to continue [y/n]? ")
    if CONTINUE_INPUT == 'y':
        try:
            with transaction.atomic():
                if os.path.isfile('{}/corp_approved_carryover.txt'.format(SCRIPT_DATA_FOLDER)):
                    corp_approved_carryover_ids = read_ids('{}/corp_approved_carryover.txt'.format(SCRIPT_DATA_FOLDER))
                    carryover_currently_approved(corp_approved_carryover_ids)
                
                if os.path.isfile('{}/carryover_without_approvals.txt'.format(SCRIPT_DATA_FOLDER)):
                    carryover_without_approvals_ids = read_ids('{}/carryover_without_approvals.txt'.format(SCRIPT_DATA_FOLDER))
                    carryover_without_approvals(carryover_without_approvals_ids)

                if os.path.isfile('{}/approve_seeking_approval.txt'.format(SCRIPT_DATA_FOLDER)):
                    seeking_approval_ids = read_ids('{}/approve_seeking_approval.txt'.format(SCRIPT_DATA_FOLDER))
                    update_seeking_approval(seeking_approval_ids)
                
                if os.path.isfile('{}/financial_year_only.txt'.format(SCRIPT_DATA_FOLDER)):
                    update_financial_year_ids = read_ids('{}/financial_year_only.txt'.format(SCRIPT_DATA_FOLDER))
                    update_financial_year(update_financial_year_ids)

                if os.path.isfile('{}/burn_priority.txt'.format(SCRIPT_DATA_FOLDER)):
                    burn_priority_tuples = read_id_tuples('{}/burn_priority.txt'.format(SCRIPT_DATA_FOLDER))
                    update_burn_priority(burn_priority_tuples)

                if os.path.isfile('{}/burn_areas.txt'.format(SCRIPT_DATA_FOLDER)):
                    burn_area_tuples = read_id_tuples('{}/burn_areas.txt'.format(SCRIPT_DATA_FOLDER))
                    update_burn_areas(burn_area_tuples)

                if os.path.isfile('{}/burn_perimeters.txt'.format(SCRIPT_DATA_FOLDER)):
                    burn_perimeter_tuples = read_id_tuples('{}/burn_perimeters.txt'.format(SCRIPT_DATA_FOLDER))
                    update_burn_perimeters(burn_perimeter_tuples)

                if os.path.isfile('{}/overall_rationales.txt'.format(SCRIPT_DATA_FOLDER)):
                    overall_rationale_tuples = read_id_tuples_pipe_separated('{}/overall_rationales.txt'.format(SCRIPT_DATA_FOLDER))
                    update_overall_rationales(overall_rationale_tuples)
                    
                if os.path.isfile('{}/contentious_change.txt'.format(SCRIPT_DATA_FOLDER)):
                    contentious_tuples = read_id_tuples('{}/contentious_change.txt'.format(SCRIPT_DATA_FOLDER))
                    update_contentious(contentious_tuples)
                    
                if os.path.isfile('{}/contentious_rationales.txt'.format(SCRIPT_DATA_FOLDER)):
                    contentious_rationale_tuples = read_id_tuples_pipe_separated('{}/contentious_rationales.txt'.format(SCRIPT_DATA_FOLDER))
                    update_contentious_rationales(contentious_rationale_tuples)

        except BaseException:
            print('Error')

    else:
        sys.exit()
"""
        
def run():
    try:
        SCRIPT_FOLDER = 'pbs/scripts'
        DATE_APPROVED_INPUT = raw_input("Please enter the date that the Burn Program was approved "
                                        "by Corporate Executive (dd/mm/yyyy): ")
        global DATE_APPROVED
        DATE_APPROVED = datetime.strptime(DATE_APPROVED_INPUT, '%d/%m/%Y').replace(tzinfo=pytz.UTC)

        if DATE_APPROVED.month != 7 or DATE_APPROVED.year != date.today().year:
            print('Can only run this script in July of the current year')
            sys.exit()

        global DATE_APPROVED_TO
        DATE_APPROVED_TO = date(DATE_APPROVED.year, 9, 30)
        global PREVIOUS_YEAR
        PREVIOUS_YEAR = '{}/{}'.format(DATE_APPROVED.year-1, DATE_APPROVED.year)
        global TARGET_YEAR
        TARGET_YEAR = '{}/{}'.format(DATE_APPROVED.year, DATE_APPROVED.year+1)
        global SCRIPT_DATA_FOLDER
        SCRIPT_DATA_FOLDER = '{}/eofy_data/{}'.format(SCRIPT_FOLDER, TARGET_YEAR.split('/')[0])

    except BaseException:
        print('Error')
        sys.exit()

    print('\nRun Script will run with the following details:')
    print(' - Previous Year: {}'.format(PREVIOUS_YEAR))
    print(' - Target Year: {}'.format(TARGET_YEAR))
    print(' - Script Data Folder: {}/'.format(SCRIPT_DATA_FOLDER))
    CONTINUE_INPUT = raw_input("Do you wish to continue [y/n]? ")
    if CONTINUE_INPUT == 'y':
        #try:
            with transaction.atomic():
                if os.path.isfile('{}/corp_approved_carryover.txt'.format(SCRIPT_DATA_FOLDER)):
                    corp_approved_carryover_ids = read_ids('{}/corp_approved_carryover.txt'.format(SCRIPT_DATA_FOLDER))
                    carryover_currently_approved(corp_approved_carryover_ids)
                    report_text.append("Corp approved carryover done")
                else:
                    report_text.append("Corp approved carryover file not found")
                if os.path.isfile('{}/carryover_without_approvals.txt'.format(SCRIPT_DATA_FOLDER)):
                    carryover_without_approvals_ids = read_ids('{}/carryover_without_approvals.txt'.format(SCRIPT_DATA_FOLDER))
                    carryover_without_approvals(carryover_without_approvals_ids)
                    report_text.append("Carry over without approvals done")
                else:
                    report_text.append("Carry over without approvals file not found")
                if os.path.isfile('{}/approve_seeking_approval.txt'.format(SCRIPT_DATA_FOLDER)):
                    seeking_approval_ids = read_ids('{}/approve_seeking_approval.txt'.format(SCRIPT_DATA_FOLDER))
                    update_seeking_approval(seeking_approval_ids)
                    report_text.append("Approve seeking approvals done")
                else:
                    report_text.append("Approve seeking approvals file not found")
                if os.path.isfile('{}/apply_corp_approval.txt'.format(SCRIPT_DATA_FOLDER)):
                    apply_corp_approval_ids = read_ids('{}/apply_corp_approval.txt'.format(SCRIPT_DATA_FOLDER))
                    apply_corp_approval(apply_corp_approval_ids)
                    report_text.append("Apply corporate approvals done")
                else:
                    report_text.append("Apply corporate approvals file not found")
                if os.path.isfile('{}/financial_year_only.txt'.format(SCRIPT_DATA_FOLDER)):
                    update_financial_year_ids = read_ids('{}/financial_year_only.txt'.format(SCRIPT_DATA_FOLDER))
                    update_financial_year(update_financial_year_ids)
                    report_text.append("Fin year done")
                else:
                    report_text.append("Fin year file not found")
                if os.path.isfile('{}/burn_priority.txt'.format(SCRIPT_DATA_FOLDER)):
                    burn_priority_tuples = read_id_tuples('{}/burn_priority.txt'.format(SCRIPT_DATA_FOLDER))
                    update_burn_priority(burn_priority_tuples)
                    report_text.append("Priority done")
                else:
                    report_text.append("Priority file not found")
                if os.path.isfile('{}/burn_areas.txt'.format(SCRIPT_DATA_FOLDER)):
                    burn_area_tuples = read_id_tuples('{}/burn_areas.txt'.format(SCRIPT_DATA_FOLDER))
                    update_burn_areas(burn_area_tuples)
                    report_text.append("Area done")
                else:
                    report_text.append("Area file not found")
                if os.path.isfile('{}/burn_perimeters.txt'.format(SCRIPT_DATA_FOLDER)):
                    burn_perimeter_tuples = read_id_tuples('{}/burn_perimeters.txt'.format(SCRIPT_DATA_FOLDER))
                    update_burn_perimeters(burn_perimeter_tuples)
                    report_text.append("Perimeter done")
                else:
                    report_text.append("Perimeter file not found")
                if os.path.isfile('{}/overall_rationales.txt'.format(SCRIPT_DATA_FOLDER)):
                    overall_rationale_tuples = read_id_tuples_pipe_separated('{}/overall_rationales.txt'.format(SCRIPT_DATA_FOLDER))
                    update_overall_rationales(overall_rationale_tuples)
                    report_text.append("Overall rationale done")
                else:
                    report_text.append("Overall rationale file not found")
                if os.path.isfile('{}/contentious_change.txt'.format(SCRIPT_DATA_FOLDER)):
                    contentious_tuples = read_id_tuples('{}/contentious_change.txt'.format(SCRIPT_DATA_FOLDER))
                    update_contentious(contentious_tuples)
                    report_text.append("Contentious change done")
                else:
                    report_text.append("Contentious change file not found")
                if os.path.isfile('{}/contentious_rationale.txt'.format(SCRIPT_DATA_FOLDER)):
                    contentious_rationale_tuples = read_id_tuples_pipe_separated('{}/contentious_rationale.txt'.format(SCRIPT_DATA_FOLDER))
                    update_contentious_rationales(contentious_rationale_tuples)
                    report_text.append("Contentious rationale done")
                else:
                    report_text.append("Contentious rationale file not found")
                # Copied from remove_approvals.py then updated
                #to_be_removed_ids = read_ids('pbs/scripts/eofy_data/2018/corp_approval_removal.txt')
                #to_be_removed_ids = read_ids('{}/remove_corporate_approval.txt'.format(SCRIPT_DATA_FOLDER))
                #remove_approvals(to_be_removed_ids)
                
                for row in report_text:
                    print(row)
        #except BaseException:
          #  print('Error')

    else:
        sys.exit()