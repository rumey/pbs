import os

from django.test import TestCase

from pbs.document.utils import get_dimensions


class GetDimensionsTests(TestCase):
    def setUp(self):
        self.path = os.path.join(os.path.dirname(__file__), 'documents')

    def test_get_dimensions_png(self):
        "Test with a good PNG"
        info = get_dimensions(os.path.join(self.path, 'test.png'))
        self.assertEqual(info.format, 'PNG')
        self.assertEqual(info.width, 2429)
        self.assertEqual(info.height, 619)
        self.assertEqual(info.units, 'px')

    def test_get_dimensions_jpg(self):
        "Test with a good JPEG"
        info = get_dimensions(os.path.join(self.path, 'test.jpg'))
        self.assertEqual(info.format, 'JPEG')
        self.assertEqual(info.width, 1600)
        self.assertEqual(info.height, 821)
        self.assertEqual(info.units, 'px')

    def test_get_dimensions_pdf(self):
        "Test with a good PDF"
        info = get_dimensions(os.path.join(self.path, 'test.pdf'))
        self.assertEqual(info.format, 'PDF')
        self.assertEqual(info.width, 595)  # 595.448
        self.assertEqual(info.height, 842)  # 842.04
        self.assertEqual(info.units, 'pt')

    def test_non_existant_document(self):
        info = get_dimensions(os.path.join(self.path, 'nonexistant.png'))
        self.assertEqual(info.format, 'PDF')
        self.assertEqual(info.width, 0)
        self.assertEqual(info.height, 0)
        self.assertEqual(info.units, 'pt')
