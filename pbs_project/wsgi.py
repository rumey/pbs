"""
WSGI config for pbs project.
It exposes the WSGI callable as a module-level variable named ``application``
"""
import confy
confy.read_environment_file('.env')  # Must precede dj_static imports.


from django.core.wsgi import get_wsgi_application
from dj_static import Cling, MediaCling

application = Cling(MediaCling(get_wsgi_application()))
