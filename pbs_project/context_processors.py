from django.conf import settings


def standard(request):
    """Dictionary of context variables to pass with every request response.
    """
    context = {
        'application_version_no': settings.APPLICATION_VERSION_NO,
    }
    return context
