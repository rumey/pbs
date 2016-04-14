from __future__ import (division, print_function, unicode_literals,
                        absolute_import)
from django.conf import settings
from django import http

import logging


logger = logging.getLogger("log." + __name__)

try:
    XS_SHARING_ALLOWED_ORIGINS = settings.XS_SHARING_ALLOWED_ORIGINS
    XS_SHARING_ALLOWED_METHODS = settings.XS_SHARING_ALLOWED_METHODS
except AttributeError:
    XS_SHARING_ALLOWED_ORIGINS = '*'
    XS_SHARING_ALLOWED_METHODS = ['POST', 'GET', 'OPTIONS', 'PUT', 'DELETE']


def get_exempt_urls():
    exempt_urls = [settings.LOGIN_URL.lstrip('/')]
    if hasattr(settings, 'LOGIN_EXEMPT_URLS'):
        exempt_urls += list(settings.LOGIN_EXEMPT_URLS)
    return exempt_urls


def cors_preflight_response(request, response=None):
    response = response or http.HttpResponse()
    if "HTTP_ORIGIN" in request.META:
        response['Access-Control-Allow-Origin'] = request.META["HTTP_ORIGIN"]
    else:
        response['Access-Control-Allow-Origin'] = XS_SHARING_ALLOWED_ORIGINS
    response['Access-Control-Allow-Methods'] = ",".join(XS_SHARING_ALLOWED_METHODS)
    response['Access-Control-Allow-Credentials'] = "true"
    if 'HTTP_ACCESS_CONTROL_REQUEST_HEADERS' in request.META:
        response['Access-Control-Allow-Headers'] = request.META["HTTP_ACCESS_CONTROL_REQUEST_HEADERS"]
    return response


class AuthenticationMiddleware(object):
    def process_request(self, request):
        if 'HTTP_ACCESS_CONTROL_REQUEST_METHOD' in request.META:
            return cors_preflight_response(request)

        # Add site name to request object (if defined).
        if hasattr(settings, 'SITE_NAME'):
            request.SITE_NAME = settings.SITE_NAME
            request.footer = " (( {0} {1} ))".format(request.SITE_NAME.split("_")[0], "11.06")

    def process_response(self, request, response):
        return cors_preflight_response(request, response)
