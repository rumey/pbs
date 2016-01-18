from __future__ import unicode_literals

import os
import tempfile

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.test import TestCase


from pbs.document.fields import ContentTypeRestrictedFileField

temp_storage_dir = tempfile.mkdtemp()
temp_storage = FileSystemStorage(temp_storage_dir)
temp_upload_to_dir = os.path.join(temp_storage.location, 'tests')
document_path = os.path.join(os.path.dirname(__file__), 'documents')


class Document(models.Model):
    limited = ContentTypeRestrictedFileField(
        storage=temp_storage, upload_to='tests', max_upload_size=100)
    unlimited = ContentTypeRestrictedFileField(
        storage=temp_storage, upload_to='tests')


class ContentTypeRestrictedFileFieldTests(TestCase):
    def test_max_upload_size_unset(self):
        "No max upload file size"

    def test_max_upload_size_set(self):
        "Make sure max upload size is enforced"
        f = ContentTypeRestrictedFileField(storage=temp_storage,
                                           upload_to='tests',
                                           max_upload_size=100)
        contents = open(os.path.join(document_path, 'test.pdf'))
        doc = SimpleUploadedFile('test.upload', contents.read(),
                                 'application/pdf')
        f.clean(f.descriptor_class(doc), None)
        self.assertRaises(ValidationError, f.clean, None, None)
