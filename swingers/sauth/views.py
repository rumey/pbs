"""
    Views for swingers to manipulate applinks::
"""
from __future__ import (division, print_function, unicode_literals,
                        absolute_import)

import os
import base64
import json

from django import http
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from swingers.sauth.models import Token
from swingers.utils.auth import validate_request


def validate_token(request):
    """
    Middleware should refresh token if required.
    Just return true/false on whether user is logged in.
    """
    if request.user.is_authenticated():
        return http.HttpResponse("true", content_type="text/plain")
    else:
        return http.HttpResponse("false", content_type="text/plain")


@csrf_exempt
def request_access_token(request):
    """
    Create tokens on a well formed request
    """
    # Validate the request, get user and applink
    try:
        user, link, expires = validate_request(request.REQUEST)
    except Exception as e:
        return http.HttpResponseForbidden(e)
    else:
        # Get existing or generate a token for the user
        try:
            token = Token.objects.filter(timeout=expires, user=user,
                                         link=link).order_by("modified")[0]
            token.modified = timezone.now()
        except IndexError:
            token = Token(secret=base64.urlsafe_b64encode(os.urandom(8)),
                          timeout=expires, user=user, link=link)
        if "url" in request.REQUEST:
            token.url = request.REQUEST["url"]
        token.save()
        return http.HttpResponse(token.secret, content_type="text/plain")


@csrf_exempt
def delete_access_token(request):
    """
    Delete access_token in a request
    """
    if "access_token" in request.REQUEST:
        secret = request.REQUEST["access_token"]
        try:
            token = Token.objects.get(secret=secret)
        except Token.DoesNotExist:
            return http.HttpResponseForbidden("Token does not exist")
        else:
            token.delete()
            return http.HttpResponse("Token {0} deleted".format(secret),
                                     content_type="text/plain")
    else:
        return http.HttpResponseForbidden("Missing access_token")


@csrf_exempt
def list_access_tokens(request):
    """
    List tokens for an available user (exact same post as requesting)
    """
    # Validate the request, get user and applink
    try:
        user, link, expires = validate_request(request.REQUEST)
    except Exception, e:
        return http.HttpResponseForbidden(repr(e))
    else:
        secrets = link.token_set.filter(user=user).values_list("secret")
        return http.HttpResponse(repr([secret[0] for secret in
                                       sorted(secrets)]),
                                 content_type="text/plain")


def session(request):
    for key in request.REQUEST.keys():
        request.session[key] = request.REQUEST[key]
    response = json.dumps(request.session._session_cache, indent=2)
    return http.HttpResponse(response, content_type="application/json")
