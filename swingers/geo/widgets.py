from __future__ import (division, print_function, unicode_literals,
                        absolute_import)
import re
import json

from django import forms
from django.utils.http import urlencode
from django.utils.safestring import mark_safe

from swingers.utils import shorthash
from swingers.utils.auth import retrieve_access_token


class GoldenEyeWidget(forms.Textarea):
    request = None
    instance = 'public'
    geom_field = None
    html_info = ''
    unique_id = shorthash(html_info)
    service = 'goldeneye'

    def __init__(self, request, instance='public', show_contents=False, mode='viewer',
                 width=800, height=400, features=None, html_info=None,
                 service='goldeneye', *args, **kwargs):
        """

        """
        self.request = request
        self.instance = instance
        self.show_contents = show_contents
        self.mode = mode
        self.width = width
        self.height = height
        self.features = features or []
        if html_info:
            self.html_info = html_info
        if service:
            self.service = service
        self.url, self.access_token = retrieve_access_token(request, self.service)
        super(GoldenEyeWidget, self).__init__(*args, **kwargs)

    def get_context(self, *args, **kwargs):
        context = super(GoldenEyeWidget, self).get_context(*args, **kwargs)
        context["ge_api"] = "//ge-dev.dec.wa.gov.au/api/geoserver/v1"
        context["strew_api"] = "//ge-dev.dec.wa.gov.au/api/strew/v1"
        return context

    def features_json(self):
        """
        Returns the geometries of passed-in features as a GeoJSON
        FeatureCollection.
        """
        if self.features:
            features_json = []
            for feature in self.features:
                if getattr(feature, self.geom_field):
                    features_json.append({
                        "type": "Feature",
                        "id": feature.pk,
                        "properties": {
                            "html_info": self.html_info.format(feature)
                        },
                        "geometry": json.loads(self.geom_field.feature.json)
                    })
            return json.dumps({
                "type": "FeatureCollection",
                "features": features_json
            })

    def url_params(self):
        '''Returns widget parameters as URL-encoded output.
        '''
        options = {
            'showcontents': self.showcontents,
            'width': self.width,
            'height': self.height,
            'access_token': self.access_token,
            'mode': self.mode
        }
        return urlencode(options)

    def render(self, name, value, attrs=None):
        output = """
            <link rel="stylesheet" href="{0}/api/geoserver/v1/static/geoserver.css" type="text/css" />
            <script src="{0}/api/geoserver/v1/static/geoserver.js"></script>
            <script src="{0}/api/geoserver/v1/workspaces/{1}.js?{2}"></script>
            <textarea id="id_{3}" name="{3}" style="display:none;">{4}</textarea>
            <div id="{3}" style="float:left;"></div>
            <script type="text/javascript">
                $(function() {{
                    new GoldenEye.SpatialView("{3}");
                }});
            </script>
            <div style="clear:both;"></div>
        """
        output = output.format(self.serviceurl, self.instance,
            self.url_params(), name, value).strip()
        return mark_safe(output)


def GoldenEyeViewer(request, features=None, geom_field="shape",
                    instance="cc/instances/public", html_info=None):
    serviceurl, access_token = retrieve_access_token(request, "goldeneye")
    uniqueid = shorthash(html_info)
    options = GEDEFAULTS
    options["spatial"] = "textarea#features_{0}".format(uniqueid)
    options["access_token"] = access_token
    options["mode"] = "viewer"
    html_info = re.sub(r"([^{]){([^{])", r"\1{0.\2", html_info)
    featuresjson = []
    for feature in features:
        if getattr(feature, geom_field):
            featuresjson.append({
                "type": "Feature",
                "id": feature.pk,
                "properties": {"html_info": html_info.format(feature)},
                "geometry": json.loads(getattr(feature, geom_field).json)
            })
    featuresjson = json.dumps({
        "type": "FeatureCollection",
        "features": featuresjson
    })
    urlparams = urlencode(options)
    output = u'''
    <link rel="stylesheet" href="{0}/api/geoserver/v1/static/geoserver.css" type="text/css" />
    <script src="{0}/api/geoserver/v1/static/geoserver.js"></script>
    <script src="{0}/api/geoserver/v1/workspaces/{1}.js?{2}"></script>
    <textarea id="features_{4}" style="display:none;">{3}</textarea>
    <div id="{4}" class="goldeneye-viewer-widget" style="float:left;"></div>
    <script type="text/javascript">
        $(function() {{
        new GoldenEye.SpatialView("{4}");
    }});
    </script>
    <div style="clear:both;"></div>
    '''.format(serviceurl, instance, urlparams, featuresjson, uniqueid).strip()
    return mark_safe(output)
