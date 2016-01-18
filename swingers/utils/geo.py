from __future__ import (division, print_function, unicode_literals,
                        absolute_import)
from django.contrib.gis.geos import Point, Polygon
from django.contrib.gis.db.models.fields import GeometryField

import math
import requests
import json


def direction_name(angle):
    """
    Returns a name for a direction given in degrees.
    Example: direction_name(0.0) returns "N"
        direction_name(90.0) returns "E"
        direction_name(152.0) returns "SSE".
    """
    direction_names = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S",
                       "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    directions_num = len(direction_names)
    directions_step = 360. / directions_num
    index = int(round(angle / directions_step))
    index %= directions_num
    return direction_names[index]


def distance_bearing(point1, point2, epsg=3577):
    """
    Returns a text representation of the distance and bearing
    from point1 to point2 in SI units using the given projection.
    Defaults to GDA94 Albers.
    point1, point2 are GEOS points
    """
    distance = (point1.transform(epsg, clone=True).distance(
        point2.transform(epsg, clone=True)) / 1000)
    center_x, center_y = point2.transform(4326, clone=True).coords
    x, y = point1.transform(4326, clone=True).coords
    angle = math.degrees(math.atan2(y - center_y, x - center_x))
    bearing = (angle + 360) % 360
    return "{0:.2f} KM {1}".format(distance, direction_name(bearing))


def text_location(geom):
    """
    Tries to use OSM Nominatim to generate a text location from a GEOS
    geometry (uses centroid).
    """
    point = geom.centroid.transform(4326, clone=True)
    lon, lat = point.coords
    url = ("http://open.mapquestapi.com/nominatim/v1/reverse.php"
           "?format=json&lon={0}&lat={1}")
    try:
        nominatim = json.loads(requests.get(url.format(lon, lat)).content)
    except Exception as e:
        return "Nominatim Error: {0}".format(e)

    if nominatim.get('error'):
        return "Nominatim Error: {0}".format(nominatim.get('error'))

    nearest_point = Point(x=float(nominatim["lon"]),
                          y=float(nominatim["lat"]), srid=4326)
    distance = distance_bearing(nearest_point, point)
    return "{0} of {1}".format(distance, nominatim["display_name"])


def transform_geom(geom=None):
    """
    Requires GDAL. Accepts a Polygon or MultiPolygon geometry, and
    returns it transformed to a projection of GDA94/MGA zone 49 through
    56, depending on the centroid.

    If the centroid lies outside the appropriate X coordinates, returns
    None instead.
    """
    if hasattr(geom, 'centroid'):
        # if you ever get an AttributeError, GeometryCollection doesn't have
        # attribute x, it's most likely because your polygon or whatever
        # doesn't have a valid centroid
        x = geom.centroid.x
        if x > 108 and x <= 114:
            srid = 28349
        elif x > 114 and x <= 120:
            srid = 28350
        elif x > 120 and x <= 126:
            srid = 28351
        elif x > 126 and x <= 132:
            srid = 28352
        elif x > 132 and x <= 138:
            srid = 28353
        elif x > 138 and x <= 144:
            srid = 28354
        elif x > 144 and x <= 150:
            srid = 28355
        elif x > 150 and x <= 156:
            srid = 28356
        else:
            return None
        return geom.transform(ct=srid, clone=True)
    else:
        return None


def find_geom_field(queryset):
    """
    Function returns geometry field name in model of queryset.
    If doesn't exist, raise ValueError.
    """
    for field in queryset.model._meta.fields:
        if isinstance(field, GeometryField):
            return field.name
    raise ValueError


SPATIAL_REF_SITE = 'http://spatialreference.org/ref/epsg/'

#Geojson field names
GEOJSON_FIELD_TYPE = 'type'
GEOJSON_FIELD_HREF = 'href'
GEOJSON_FIELD_PROPERTIES = 'properties'
GEOJSON_FIELD_CRS = 'crs'
GEOJSON_FIELD_SRID = 'srid'
GEOJSON_FIELD_GEOMETRY = 'geometry'
GEOJSON_FIELD_FEATURES = 'features'
GEOJSON_FIELD_BBOX = 'bbox'
GEOJSON_FIELD_ID = 'id'

#Geojson field values
GEOJSON_VALUE_LINK = 'link'
GEOJSON_VALUE_FEATURE = 'Feature'
GEOJSON_VALUE_FEATURE_COLLECTION = 'FeatureCollection'


def __simple_render_to_json(obj):
    '''
    Converts python objects to simple json objects (int, float, string)
    '''
    if type(obj) == int or type(obj) == float or type(obj) == bool:
        return obj
    elif type(obj) == unicode:
        return obj.encode("utf-8")
    else:
        return str(obj)


def render_to_geojson(queryset, projection=None, simplify=None,
                      extent=None, maxfeatures=None, priority_field=None,
                      properties=None, prettyprint=False):
    """
    Shortcut to render a GeoJson FeatureCollection from a Django QuerySet.
    Currently computes a bbox and adds a crs member as a sr.org link.
    Parameters:
    * queryset of models containing geometry data
    * projection used when geometry data should be transformed to other
      projection.
    * simplify (float) value specifies tolerance in Douglas-Peucker
      algorithm for simplifying geometry
    * extent (django.contrib.gis.geos.Polygon instance) that which
      bounds rendered features
    * maxfeatures parameter gives maximum number of rendered features
      based on priority field.
    * priorityfield (string) - name of the priority field used for
      reducing features
    * properties - list of model's non geometry fields names included in
      geojson
    * prettyprint flag influencing indentation used in geojson (for
      better readability)
    """
    geom_field = find_geom_field(queryset)

    if extent is not None:
        #queryset.filter(<geom_field>__intersects=extent)
        queryset = queryset.filter(**{'%s__intersects' % geom_field: extent})

    if maxfeatures is not None:
        if priority_field is None:
            raise RuntimeError("priorityfield must be defined")
        queryset.order_by(priority_field)
        queryset = queryset[:maxfeatures]

    src_projection = None
    if queryset.exists():
        src_projection = getattr(queryset[0], geom_field).srid

    if projection is None:
        projection = src_projection

    if projection is not None and src_projection != projection:
        queryset = queryset.transform(projection)

    if properties is None:
        properties = [field.name for field in queryset.model._meta.fields]

    features = list()
    collection = dict()
    if src_projection is not None:
        crs = dict()
        crs[GEOJSON_FIELD_TYPE] = GEOJSON_VALUE_LINK
        crs_properties = dict()
        crs_properties[GEOJSON_FIELD_HREF] = '%s%s/' % (SPATIAL_REF_SITE,
                                                        projection)
        crs_properties[GEOJSON_FIELD_TYPE] = 'proj4'
        crs[GEOJSON_FIELD_PROPERTIES] = crs_properties
        collection[GEOJSON_FIELD_CRS] = crs
        collection[GEOJSON_FIELD_SRID] = projection
    for item in queryset:
        feat = dict()
        feat[GEOJSON_FIELD_ID] = item.pk

        #filling feature properties with dict: {<field_name>:<field_value>}
        feat[GEOJSON_FIELD_PROPERTIES] = dict()
        for fname in properties:
            if fname == geom_field:
                continue
            feat[GEOJSON_FIELD_PROPERTIES][fname] = __simple_render_to_json(
                getattr(item, fname))
        feat[GEOJSON_FIELD_TYPE] = GEOJSON_VALUE_FEATURE
        geom = getattr(item, geom_field)
        if simplify is not None:
            geom = geom.simplify(simplify)
        feat[GEOJSON_FIELD_GEOMETRY] = json.loads(geom.geojson)
        features.append(feat)

    collection[GEOJSON_FIELD_TYPE] = GEOJSON_VALUE_FEATURE_COLLECTION
    collection[GEOJSON_FIELD_FEATURES] = features

    if queryset.exists():
        if projection is not None and src_projection != projection:
            poly = Polygon.from_bbox(queryset.extent())
            poly.srid = src_projection
            poly.transform(projection)
            collection[GEOJSON_FIELD_BBOX] = poly.extent
        else:
            collection[GEOJSON_FIELD_BBOX] = queryset.extent()

    if prettyprint:
        return json.dumps(collection, indent=4)
    else:
        return json.dumps(collection)
