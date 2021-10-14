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
    return [i[0].strip() for i in list(csv.reader(open(filename), delimiter=',', quotechar='"'))]

def remove_approvals(ids):
    # Copied in from remove_approvals.py then updated
    # Used to remove corporate approval from ePFPs
    print('\nClearing approvals for ePFPs currently approved for {}'.format(PREVIOUS_YEAR))
    updated_count = 0
    burn_count = 0
    input_data_count = len([burn_id for burn_id in ids if burn_id != ""])
    for p in Prescription.objects.filter(burn_id__in=ids).order_by('burn_id'):
        if p.financial_year != PREVIOUS_YEAR:
            print('Financial year for {} is not {}.'.format(str(p.burn_id), PREVIOUS_YEAR))
        else:
            if (p.status != 2): # burn status must not be closed
                p.planning_status = 1
                p.save()
                updated_count += 1
            else:
                print('Burn status for {} is closed'.format(str(p.burn_id)))
        burn_count += 1
    print 'Cleared approvals for {} ePFPs; expected {} and rejected {}.'.format(updated_count, input_data_count, burn_count - updated_count)
                
def run():
    try:
        SCRIPT_FOLDER = 'pbs/scripts'
        DATE_APPROVED_INPUT = raw_input("Please enter the date that removal from the approved Burn Program was approved by Corporate Executive (dd/mm/yyyy): ")
        global DATE_APPROVED
        DATE_APPROVED = datetime.strptime(DATE_APPROVED_INPUT, '%d/%m/%Y').replace(tzinfo=pytz.UTC)

        if DATE_APPROVED.month != 7 or DATE_APPROVED.year != date.today().year:
            print('Can only run this script in July of the current year')
            sys.exit()

        global PREVIOUS_YEAR
        PREVIOUS_YEAR = '{}/{}'.format(DATE_APPROVED.year-1, DATE_APPROVED.year)
        global SCRIPT_DATA_FOLDER
        SCRIPT_DATA_FOLDER = '{}/eofy_data/{}'.format(SCRIPT_FOLDER, TARGET_YEAR.split('/')[0])

    except BaseException:
        print('Error')
        sys.exit()

    print('\nRun Script will run with the following details:')
    print(' - Previous Year: {}'.format(PREVIOUS_YEAR))
    print(' - Script Data Folder: {}/'.format(SCRIPT_DATA_FOLDER))
    CONTINUE_INPUT = raw_input("Do you wish to continue [y/n]? ")
    if CONTINUE_INPUT == 'y':
        to_be_removed_ids = read_ids(('{}//remove_corporate_approval.txt'.format(SCRIPT_DATA_FOLDER))