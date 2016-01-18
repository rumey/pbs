from django.test import TestCase

from swingers.tests.admin import ParentDuckAdmin
from swingers.tests.models import GrandParentDuck, ParentDuck, Duck
from swingers.sauth.sites import AuditSite


class AdminTests(TestCase):
    fixtures = ['test-users']

    def setUp(self):
        pass

    def test_RelatedFieldAdmin(self):
        duck = Duck.objects.create(name='duck')
        parent_duck = ParentDuck.objects.create(name='parent_duck', duck=duck)
        grand_parent_duck = GrandParentDuck.objects.create(
            name='grand_parent_duck', duck=parent_duck)
        model = GrandParentDuck
        site = AuditSite()
        model_admin = ParentDuckAdmin(model, site)

        getter = getattr(model_admin, 'duck__duck__name')
        self.assertEqual(getter.admin_order_field, 'duck__duck__name')
        self.assertEqual(getter.short_description, 'Name')
        self.assertEqual(getter(model_admin, grand_parent_duck),  duck.name)

        getter = getattr(model_admin, 'duck__duck')
        self.assertEqual(getter.admin_order_field, 'duck__duck')
        self.assertEqual(getter.short_description, 'Duck')
        self.assertEqual(getter(model_admin, grand_parent_duck),  duck)
