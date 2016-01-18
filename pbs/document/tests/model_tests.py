import os

from django.test import TestCase
from django.test.utils import override_settings

from pbs.document.models import Document, DocumentTag

document_path = os.path.join(os.path.dirname(__file__), 'documents')


@override_settings(MEDIA_ROOT=document_path)
class DocumentTests(TestCase):
    def test_create_document(self):
        path = os.path.join(document_path, 'test.pdf')
        tag = DocumentTag.objects.get(name="Orthophotography Map")
        document = Document.objects.create(
            category=tag.category, tag=tag, document=path)
        self.assertTrue(document.pk is not None)
        self.assertEqual(document.descriptor, document.tag.name)

    def test_descriptor_other(self):
        path = os.path.join(document_path, 'test.pdf')
        tag = DocumentTag.objects.get(name="Orthophotography Map")
        document = Document.objects.create(
            category=tag.category, tag=tag, document=path,
            custom_tag="test")
        self.assertEqual(document.descriptor, "Other (test)")

    def test_filename(self):
        path = os.path.join(document_path, 'test.pdf')
        tag = DocumentTag.objects.get(name="Orthophotography Map")
        document = Document.objects.create(
            category=tag.category, tag=tag, document=path,
            custom_tag="test")
        self.assertEqual(document.filename,
                         os.path.basename(document.document.path))
