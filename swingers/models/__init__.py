from django.db import connections


GIS_ENABLED = False
# check the db support first
if (any(hasattr(connection.ops, 'spatial_version')
        for connection in connections.all())):
    # It's possible a project doesn't have `django.contrib.gis` in its
    # INSTALLED_APPS, fallback to `django.db.models` if so.
    try:
        from django.contrib.gis.db.models import *
        from django.contrib.gis.db.models import GeoManager as Manager
        from swingers.models.base import ActiveGeoModel as ActiveModel
        from swingers.models.managers import (ActiveGeoModelManager as
                                                   ActiveModelManager)
        GIS_ENABLED = True
    except ImportError:
        pass

if not GIS_ENABLED:
    from django.db.models import *
    from swingers.models.base import ActiveModel
    from swingers.models.managers import ActiveModelManager

from swingers.models.fields import *
from swingers.models.geo import *
from swingers.models.auth import *
