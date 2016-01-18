
from django.core.exceptions import ValidationError

from pbs.tests import BasePbsTestCase
from pbs.implementation.models import LightingSequence


class LightingSequenceTestCase(BasePbsTestCase):
    def setUp(self):
        self.prescription = self.make('Prescription')

    def test_clean_fuel_age(self):
        ls = LightingSequence.objects.create(prescription=self.prescription,
                                             seqno=1, cellname="bla",
                                             fuel_age=None, strategies="bla",
                                             wind_dir="bla",
                                             fuel_description="bleee")
        with self.assertRaises(ValidationError) as cm:
            ls.full_clean()
            self.assertEqual(cm.exception.messages_dict, {
                'fuel_age': [u"You must enter a fuel age or tick Fuel " +
                             "Age Unknown."]})

        ls.fuel_age = 3
        ls.full_clean()

        ls.fuel_age_unknown = True
        with self.assertRaises(ValidationError) as cm:
            ls.full_clean()
            self.assertEqual(cm.exception.messages_dict, {
                'fuel_age': [u"You must either enter a fuel age or tick " +
                             "Fuel Age Unknown."]})

        ls.fuel_age = None
        ls.fuel_age_unknown = True
        ls.full_clean()
