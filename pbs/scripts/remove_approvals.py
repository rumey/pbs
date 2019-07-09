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

def remove_approvals(ids):
    # Used to remove corporate approval from ePFPs
    print('\nClearing approvals for ePFPs currently approved for 2017/2018.')
    count = 0
    for p in Prescription.objects.filter(burn_id__in=ids,financial_year='2017/2018'):
        if (p.financial_year != '2017/2018'):
            print('Financial year for {} is not 2017/2018.'.format(str(p.burn_id)))
        else:
            if (p.status != 2): # burn status must not be closed
                p.clear_approvals()
                p.save()
                count += 1
            else:
                print('Burn status for {} is closed'.format(str(p.burn_id)))
    print 'Cleared approvals for {} ePFPs'.format(count)


if __name__ == "__main__":
    to_be_removed_ids = read_ids('pbs/scripts/eofy_data/2018/corp_approval_removal.txt')
    remove_approvals(to_be_removed_ids)
