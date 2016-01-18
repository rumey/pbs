from datetime import date
from django.conf import settings


def standard(request):
    '''
    Define a dictionary of context variables to pass to every template.
    '''
    # Determine if this site is Dev/Test/UAT/Prod
    hostenv = settings.HOSTNAME.split('-')[-1]
    if hostenv != 'prod':
        production_site = False
    else:
        production_site = True
    extra_footer = ''
    # The dictionary below will be passed to all templates.
    context = {
        'sitetitle': settings.SITE_TITLE,
        'application_version_no': settings.APPLICATION_VERSION_NO,
        'production_site': production_site,
        'hostenv': hostenv.capitalize(),
        'date_today': date.today(),
        'extra_footer': extra_footer,
        'DEC_CDN': settings.DEC_CDN,
        'CDNJS_URL': settings.CDNJS_URL,
        'PERSONA_LOGIN': settings.PERSONA_LOGIN
    }
    context.update(settings.STATIC_CONTEXT_VARS)
    return context
