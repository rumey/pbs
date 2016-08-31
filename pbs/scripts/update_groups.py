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
from pbs.prescription.models import Prescription

from django.contrib.auth.models import User, Group

rdo = Group.objects.get(name='Regional Duty Officer')
sdo = Group.objects.get(name='State Duty Officer')
sdoa = Group.objects.get(name='State Duty Officer Assistant')

def add_groups():

    users = [i for i in list(csv.reader(open('pbs/scripts/daily_burn_programs_groups.txt'), delimiter=',', quotechar='"'))]
    for user in users:
        first_name = user[0].split(' ')[0]
        if len(user[0].split(' '))==3:
            last_name = ' '.join([user[0].split(' ')[1], user[0].split(' ')[2]]) # concat middle and last name
        else:
            last_name = user[0].split(' ')[1]
        group = user[1]
        try:
            u = User.objects.get(first_name=first_name, last_name=last_name)
            if group == 'RDO':
                rdo.user_set.add(u)
            elif group == 'SDO':
                sdo.user_set.add(u)
            elif group == 'SDOA':
                sdoa.user_set.add(u)
            else:
                print('Unknown GROUP: {}'.format(group))

        except:
            print('Cannot get unique username for user: {}'.format(user))


if __name__ == "__main__":
    add_groups()
