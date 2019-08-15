from django import http
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.models import User


class SSOLoginMiddleware(object):
    def process_request(self, request):
        if request.path.startswith('/logout') and "HTTP_X_LOGOUT_URL" in request.META:
            logout(request)
            return http.HttpResponseRedirect(request.META["HTTP_X_LOGOUT_URL"])
        if not request.user.is_authenticated() and "HTTP_REMOTE_USER" in request.META:
            attributemap = {
                "username": "HTTP_REMOTE_USER",
                "last_name": "HTTP_X_LAST_NAME",
                "first_name": "HTTP_X_FIRST_NAME",
                "email": "HTTP_X_EMAIL",
            }

            for key, value in attributemap.iteritems():
                attributemap[key] = request.META[value]
            
            if hasattr(settings, "ALLOWED_EMAIL_SUFFIXES") and settings.ALLOWED_EMAIL_SUFFIXES:
                allowed = settings.ALLOWED_EMAIL_SUFFIXES
                if isinstance(settings.ALLOWED_EMAIL_SUFFIXES, basestring):
                    allowed = [settings.ALLOWED_EMAIL_SUFFIXES]
                if not any([attributemap["email"].lower().endswith(x) for x in allowed]):
                    return http.HttpResponseForbidden()

            if User.objects.filter(email__istartswith=attributemap["email"]).exists():
                user = User.objects.get(email__istartswith=attributemap["email"])
            elif User.objects.filter(username__iexact=attributemap["username"]).exists():
                user = User.objects.get(username__iexact=attributemap["username"])
            else:
                user = User()
            user.__dict__.update(attributemap)
            user.save()
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
