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

# Script starts here                                                                                                                                                                                         
import csv 
from pbs.prescription.models import Prescription

burn_ids = [i[0] for i in list(csv.reader(open('pbs/scripts/approvals_list.txt'), delimiter=',', quotechar='"'))]

count = 0 
for p in Prescription.objects.filter(planning_status=3):
    p.planning_status = 1 
#    p.save()
    count += 1
print 'Removed Corporate Approval from {} ePFPs'.format(count)

count = 0 
for p in Prescription.objects.filter(burn_id__in=burn_ids):
    p.planning_status = 3 
    p.save()
    count += 1
print 'Applied Corporate Approval to {} ePFPs (of {})'.format(count, len(burn_ids))
