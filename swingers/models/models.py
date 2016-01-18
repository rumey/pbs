from __future__ import (division, print_function, unicode_literals,
                        absolute_import)

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

from swingers import models
from swingers.models import Audit, ActiveModel
from swingers.utils import content_filename

import logging
import os


logger = logging.getLogger("log." + __name__)


class RegionAbstract(Audit, ActiveModel):
    """
    Abstract model to represent DEC regions and district areas, for use
    within other DEC corporate applications.
    """
    name = models.CharField(max_length=320, unique=True)
    description = models.TextField(null=True, blank=True)
    slug = models.SlugField(unique=True, help_text='Must be unique.')

    class Meta:
        abstract = True
        ordering = ['name']

    def __unicode__(self):
        return unicode(self.name)
    search_fields = ('name', 'slug', 'description')


class DocumentAbstract(Audit, ActiveModel):
    '''
    Generic class for supporting documents.
    '''
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    uploaded_file = models.FileField(
        # max_length is maximum full path and filename length:
        max_length=255,
        upload_to=content_filename)
    description = models.TextField(
        blank=True, null=True,
        help_text='Name and/or description of the supporting document.')

    class Meta:
        abstract = True

    def __unicode__(self):
        return unicode(self.pk)

    @property
    def uploaded_file_name(self):
        """
        Return the file name of the uploaded file, minus the server file path.
        """
        try:
            return self.uploaded_file.name.rsplit('/', 1)[-1]
        except:
            # If the file has been deleted/is missing, return a warning.
            return '<missing_file>'

    @property
    def uploaded_file_ext(self):
        '''
        Return the file extension of the uploaded file.
        '''
        try:
            ext = os.path.splitext(self.uploaded_file.name)[1]
            return ext.replace('.', '').upper()
        except:
            # If the file has been deleted/is missing, return an empty string.
            return ''

    @property
    def filesize_str(self):
        '''
        Return the filesize as a nicely human-readable string.
        '''
        try:
            num = self.uploaded_file.size
            for x in ['bytes', 'KB', 'MB', 'GB']:
                if num < 1024.0:
                    return '%3.1f%s' % (num, x)
                num /= 1024.0
        except:
            # If the file has been deleted/is missing, return an empty string.
            return ''
