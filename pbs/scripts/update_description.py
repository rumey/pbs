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

from pbs.prescription.models import Prescription

def update():
    for p in Prescription.objects.all():
        p.description = p.generate_description()
        p.save()


if __name__ == "__main__":
    update()
