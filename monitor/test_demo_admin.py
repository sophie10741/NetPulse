import os
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase


class CreateDemoAdminTests(TestCase):
    def test_creates_superuser_only_once(self):
        env = {"NETPULSE_ADMIN_USER": "demo", "NETPULSE_ADMIN_PASSWORD": "S3cret-pass-1"}
        with patch.dict(os.environ, env):
            call_command("create_demo_admin", stdout=StringIO())
            call_command("create_demo_admin", stdout=StringIO())

        users = get_user_model().objects
        self.assertEqual(users.filter(is_superuser=True).count(), 1)
        self.assertTrue(users.get(username="demo").check_password("S3cret-pass-1"))
