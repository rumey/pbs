"""
WSGI config for sdis project.
It exposes the WSGI callable as a module-level variable named ``application``
"""
import confy
from django.core.wsgi import get_wsgi_application
from dj_static import Cling, MediaCling
import os

confy.read_environment_file('.env')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pbs_project.settings")
application = Cling(MediaCling(get_wsgi_application()))
