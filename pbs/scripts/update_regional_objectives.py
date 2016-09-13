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

from pbs.prescription.models import Purpose


def add_ordering():

    try:
        # update the name
        pp = Purpose.objects.get(name='Water Catchment')
        pp.name = 'Water Catchment Management'
        pp.save()
        print('Updated Purpose Name: {}'.format(pp.name))

        # update the ordering
        count = 0
        for i in Purpose.objects.all():                    
            if i.name!='Bushfire Risk Management':
                i.display_order=2
                i.save()
                count += 1
        print('Updated Purposes Ordering: {}'.format(count))
    except:
        raise Exception('ERROR assigning ordering to Purposes Display')


if __name__ == "__main__":
    add_ordering()
