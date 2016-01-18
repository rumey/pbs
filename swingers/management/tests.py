from django.test import TestCase


class ManagementTests(TestCase):
    def test_commands_can_be_found(self):
        from swingers.management.commands.create_db import Command
        from swingers.management.commands.deploy import Command
        from swingers.management.commands.drop_create_db import Command
        from swingers.management.commands.metrics import Command
        from swingers.management.commands.quickdeploy import Command
        from swingers.management.commands.syncdbmigrate import Command
