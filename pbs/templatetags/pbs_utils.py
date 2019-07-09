from django.conf import settings
from django.shortcuts import resolve_url
from django import template


register = template.Library()


@register.simple_tag
def login_url():
    return resolve_url(settings.LOGIN_URL)

@register.simple_tag
def page_background():
    """
    Usage:
        Set a image as html page's background to indicate the runtime environment (dev or uat)
    """
    if settings.ENV_TYPE == "PROD":
        return ""
    elif settings.ENV_TYPE == "LOCAL":
        return "background-image:url('/static/img/local.png')"
    elif settings.ENV_TYPE == "DEV":
        return "background-image:url('/static/img/dev.png')"
    elif settings.ENV_TYPE == "UAT":
        return "background-image:url('/static/img/uat.png')"
    elif settings.ENV_TYPE == "TEST":
        return "background-image:url('/static/img/test.png')"
    elif settings.ENV_TYPE == "TRAINING":
        return "background-image:url('/static/img/training.png')"
    else:
        return "background-image:url('/static/img/dev.png')"

