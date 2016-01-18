from django.core.exceptions import ImproperlyConfigured
from django import forms
from django.test import TestCase
from django.contrib.gis.db.models import GeoManager
from django.db.models import Manager
from django.conf import settings

from swingers import models
from swingers.tests.models import ActiveDuck
from swingers.models import Audit
from swingers.tests.constants import SMALL_FILE, EMPTY_FILE, FILE

import operator


class ActiveModelTests(TestCase):
    cleans_up_after_itself = True

    def setUp(self):
        self.duck = ActiveDuck()
        self.duck.save()

    def test_ActiveModel_delete(self):
        self.assertNotEqual(self.duck.effective_from, None)
        self.assertEqual(self.duck.effective_to, None)
        self.assertQuerysetEqual(ActiveDuck.objects.all(), [self.duck.id],
                                 transform=operator.attrgetter('id'))
        self.assertTrue(self.duck.is_active())
        self.assertFalse(self.duck.is_deleted())
        self.assertQuerysetEqual(ActiveDuck.objects_all.all(), [self.duck.id],
                                 transform=operator.attrgetter('id'))

        self.duck.delete()
        self.assertNotEqual(self.duck.effective_from, None)
        self.assertNotEqual(self.duck.effective_to, None)
        self.assertQuerysetEqual(ActiveDuck.objects.all(), [],
                                 transform=operator.attrgetter('id'))
        self.assertFalse(self.duck.is_active())
        self.assertTrue(self.duck.is_deleted())
        self.assertQuerysetEqual(ActiveDuck.objects_all.all(), [self.duck.id],
                                 transform=operator.attrgetter('id'))

    def test_ActiveModel_bulk_delete(self):
        self.assertEqual(self.duck.effective_to, None)

        ActiveDuck.objects.filter(id__in=[self.duck.id]).delete()
        self.duck = ActiveDuck.objects_all.get(id=self.duck.id)
        self.assertNotEqual(self.duck.effective_from, None)
        self.assertNotEqual(self.duck.effective_to, None)
        self.assertFalse(self.duck.is_active())
        self.assertTrue(self.duck.is_deleted())
        self.assertQuerysetEqual(ActiveDuck.objects.all(), [],
                                 transform=operator.attrgetter('id'))
        self.assertQuerysetEqual(ActiveDuck.objects_all.all(), [self.duck.id],
                                 transform=operator.attrgetter('id'))

    def test_ActiveModel_wrong_objects_manager(self):
        class WrongActiveModel(models.ActiveModel):
            objects = Manager()
        self.assertRaises(ImproperlyConfigured, WrongActiveModel)


class FieldTests(TestCase):
    def test_contentTypeRestrictedFileField(self):
        filetype_error = 'Not permitted.'
        max_file_size_error = 'Maximum filesize.'
        error_messages = {'filetype': filetype_error,
                          'max_size': max_file_size_error}

        class FileDuck(Audit):
            f = models.ContentTypeRestrictedFileField(
                content_types=['text/plain'], max_upload_size=1024,
                upload_to=":)", error_messages=error_messages)

        d = FileDuck(f=SMALL_FILE)
        d.clean_fields(exclude=tuple())

        with self.assertRaises(forms.ValidationError) as cm:
            d = FileDuck(f=FILE)
            d.clean_fields(exclude=tuple())
        self.assertEqual(cm.exception.message_dict['f'], [max_file_size_error])

        with self.assertRaises(forms.ValidationError) as cm:
            d = FileDuck(f=EMPTY_FILE)
            d.clean_fields(exclude=tuple())
        self.assertEqual(cm.exception.message_dict['f'], [filetype_error])


class ModelImportsTests(TestCase):
    def test_imports(self):
        from swingers import models

        # check all these are exposed via models.*
        models.Model
        models.ForeignKey(ActiveDuck)
        models.Manager()
        models.ActiveModel
        models.ActiveModelManager()
        models.Audit

        self.assertEqual(models.GIS_ENABLED,
                         getattr(settings, 'GIS_ENABLED', False))

        if models.GIS_ENABLED:
            self.assertTrue(issubclass(models.Manager, GeoManager))
            self.assertTrue(issubclass(models.ActiveModel,
                                       models.base.ActiveGeoModel))
            self.assertTrue(issubclass(models.ActiveModelManager,
                                       models.managers.ActiveGeoModelManager))
        else:
            self.assertTrue(issubclass(models.Manager, Manager))
            self.assertFalse(issubclass(models.ActiveModel,
                                        models.base.ActiveGeoModel))
            self.assertFalse(issubclass(models.ActiveModelManager,
                                        models.managers.ActiveGeoModelManager))

        # check the GEO stuff validates
        models.managers.ActiveGeoModelManager()
        models.managers.ActiveGeoQuerySet(ActiveDuck)
        models.base.ActiveGeoModel

        # check the normal stuff validates
        models.managers.ActiveModelManager()
        models.managers.ActiveQuerySet(ActiveDuck)
        models.base.ActiveModel
