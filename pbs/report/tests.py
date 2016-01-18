from __future__ import unicode_literals

from django.core.exceptions import ValidationError

from pbs.report.models import AreaAchievement
from pbs.risk.models import Action, Risk, Register
from pbs.tests import BasePbsTestCase


class SummaryCompletionStateTests(BasePbsTestCase):
    def setUp(self):
        self.prescription = self.make('Prescription')

    def test_risk_register_required(self):
        pre_state = self.prescription.pre_state
        self.assertFalse(pre_state.risk_register)

        pre_state.risk_register = True
        with self.assertRaises(ValidationError) as error:
            pre_state.full_clean()
            self.assertEqual(error.exception.messages_dict, {
                'risk_register': ["To mark the risk register as complete you "
                                  "need to have at least one risk register "
                                  "item"]})

        Register.objects.create(prescription=self.prescription)
        self.assertFalse(pre_state.risk_register)
        pre_state.risk_register = True
        pre_state.full_clean()


class BurnImplementationStateTests(BasePbsTestCase):
    def test_pre_burn_actions(self):
        """
        Test that marking pre-burn actions as complete works as expected.
        """
        p = self.make('Prescription')
        day_state = p.day_state
        self.assertFalse(day_state.pre_actions)
        day_state.pre_actions = True

        # try marking pre-burn actions as complete without any actions
        with self.assertRaises(ValidationError) as cm:
            day_state.full_clean()
            self.assertEqual(cm.exception.messages_dict, {
                'pre_actions': ["Pre-burn actions cannot be marked as "
                                "complete unless there is at least one "
                                "pre-burn action associated with the burn."]})

        # try marking pre-burn actions as not applicable without any actions
        day_state.pre_actions = None
        day_state.full_clean()

        # try marking pre-burn actions as complete without filling in details
        risk = Risk.objects.filter(prescription=p)[0]
        action = Action.objects.create(risk=risk, pre_burn=True)

        day_state = p.day_state
        self.assertFalse(day_state.pre_actions)
        day_state.pre_actions = True

        with self.assertRaises(ValidationError) as cm:
            day_state.full_clean()
            self.assertEqual(cm.exception.messages_dict, {
                'pre_actions': ["Pre-burn actions cannot be marked as complete"
                                "unless all pre-burn actions have details."]})

        action.details = "Test details"
        action.save()

        self.assertFalse(day_state.pre_actions)
        day_state.pre_actions = True
        day_state.full_clean()
        day_state.save()

    def test_day_of_burn_actions(self):
        """
        Test that marking day of burn actions as complete works as expected.
        """
        p = self.make('Prescription')
        day_state = p.day_state
        self.assertFalse(day_state.actions)
        day_state.actions = True

        # try marking day of burn actions as complete without any actions
        with self.assertRaises(ValidationError) as cm:
            day_state.full_clean()
            self.assertEqual(cm.exception.messages_dict, {
                'actions': ["Day of burn actions cannot be marked as "
                            "complete unless there is at least one day "
                            "of burn action associated with the burn."]})

        # try marking day of burn actions as not applicable without any actions
        day_state.actions = None
        day_state.full_clean()

        # try marking day of burn actions as complete without having action
        # details filled in
        risk = Risk.objects.filter(prescription=p)[0]
        action = Action.objects.create(risk=risk, day_of_burn=True)

        day_state.actions = True

        with self.assertRaises(ValidationError) as cm:
            day_state.full_clean()
            self.assertEqual(cm.exception.messages_dict, {
                'actions': ["Day of burn actions cannot be marked as "
                            "complete unless all day of burn actions have "
                            "details."]})

        action.details = "Test details"
        action.save()

        self.assertFalse(day_state.actions)
        day_state.actions = True
        day_state.full_clean()
        day_state.save()


class BurnClosureStateTests(BasePbsTestCase):
    def test_post_burn_actions_not_applicable(self):
        p = self.make('Prescription')
        post_state = p.post_state
        self.assertFalse(post_state.post_actions)

        # try marking post-burn actions as not applicable without any actions
        post_state.post_actions = True
        post_state.full_clean()

        risk = Risk.objects.filter(prescription=p)[0]
        Action.objects.create(risk=risk, post_burn=True)

        with self.assertRaises(ValidationError) as error:
            post_state.full_clean()
            self.assertEqual(error.exception.messages_dict, {
                'post_actions': ["You cannot mark post-burn actions as not "
                                 "applicable if there are any post-burn "
                                 "actions."]})


class AreaAchievementTests(BasePbsTestCase):
    def setUp(self):
        self.prescription = self.make('Prescription')

    def test_edging_depth_and_length_not_mandatory(self):
        """
        Test that the length of edging and the depth of edging aren't required
        fields.
        """
        achievement = AreaAchievement(prescription=self.prescription,
                                      area_treated='1.0', area_estimate='1.0')
        achievement.full_clean()
