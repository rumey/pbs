from django.conf.urls import patterns, include, url

from django_downloadview import ObjectDownloadView

from pbs.document.models import Document
from pbs.sites import site
from pbs.forms import PbsPasswordResetForm

handler500 = 'pbs.views.handler500'
# Define the simplest possible view for Document uploads.
document_download = ObjectDownloadView.as_view(model=Document, file_field='document')

urlpatterns = patterns('',
    (r'^docs/', include('django.contrib.admindocs.urls')),
    url(r'^select2/', include('django_select2.urls')),
    (r'^', include('pbs.registration.urls')),
    # the password reset must come before site.urls, site.urls match all
    url(r'^password_reset/$', 'django.contrib.auth.views.password_reset',
        {'password_reset_form': PbsPasswordResetForm}, name='password_reset'),
    (r'^', include(site.urls)),
    (r'^', include('django.contrib.auth.urls')),
    url(r'^chaining/', include('smart_selects.urls')),
    url('^documents/(?P<pk>\d+)/download$', document_download, name='document_download'),
)
