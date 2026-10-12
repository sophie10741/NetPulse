import contextlib
import io
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from monitor.models import Connection, NetworkDevice, NetworkInterface


class NetworkDeviceTests(TestCase):
    def setUp(self):
        self.device = NetworkDevice.objects.create(name="HQ-RTR", device_type="router")

    def _add_interface(self, name, mac, ip):
        return NetworkInterface.objects.create(
            device=self.device, interface_name=name, mac_address=mac, ip_address=ip
        )

    def test_ip_address_is_none_without_interfaces(self):
        self.assertIsNone(self.device.ip_address)

    def test_ip_address_returns_first_interface_with_ip(self):
        self._add_interface("eth0", "00:11:22:33:44:55", None)
        self._add_interface("eth1", "00:11:22:33:44:66", "10.0.0.1")
        self._add_interface("eth2", "00:11:22:33:44:77", "10.0.1.1")
        self.assertEqual(self.device.ip_address, "10.0.0.1")

    @patch("monitor.ping_check.check_ping", return_value=False)
    def test_status_becomes_offline_when_ping_fails(self, _mock):
        self._add_interface("eth0", "00:11:22:33:44:55", "10.0.0.1")
        self.device.check_and_update_status()
        self.device.refresh_from_db()
        self.assertEqual(self.device.status, "offline")

    def test_status_unchanged_without_ip(self):
        self.device.check_and_update_status()
        self.device.refresh_from_db()
        self.assertEqual(self.device.status, "online")

    def test_connection_str(self):
        other = NetworkDevice.objects.create(name="BR-RTR", device_type="router")
        conn = Connection.objects.create(source=self.device, target=other)
        self.assertEqual(str(conn), "HQ-RTR → BR-RTR")


class AccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("tester", password="StrongPass123")

    def test_anonymous_is_redirected_from_home(self):
        response = self.client.get("/")
        self.assertRedirects(
            response, "/access-denied/?next=/", fetch_redirect_response=False
        )

    def test_access_denied_page_renders(self):
        self.assertEqual(self.client.get("/access-denied/").status_code, 200)

    def test_home_opens_for_logged_in_user(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/").status_code, 200)


class LoginTests(TestCase):
    def setUp(self):
        User.objects.create_user("tester", password="StrongPass123")

    def test_login_success(self):
        response = self.client.post(
            reverse("login"), {"username": "tester", "password": "StrongPass123"}
        )
        self.assertEqual(response.json(), {"success": True})

    def test_login_wrong_password(self):
        response = self.client.post(
            reverse("login"), {"username": "tester", "password": "wrong"}
        )
        self.assertFalse(response.json()["success"])

    def test_password_is_not_printed_to_console(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            self.client.post(
                reverse("login"), {"username": "tester", "password": "StrongPass123"}
            )
        self.assertNotIn("StrongPass123", buffer.getvalue())


class SshCommandViewTests(TestCase):
    def setUp(self):
        user = User.objects.create_user("tester", password="StrongPass123")
        self.client.force_login(user)
        self.device = NetworkDevice.objects.create(
            name="HQ-SRV", device_type="server", ssh_username="root"
        )
        NetworkInterface.objects.create(
            device=self.device,
            interface_name="eth0",
            mac_address="aa:bb:cc:dd:ee:ff",
            ip_address="10.0.0.5",
        )

    @patch("monitor.views.execute_ssh_command", return_value="ok")
    def test_command_uses_interface_ip(self, mocked):
        response = self.client.post(
            reverse("ssh_command", args=[self.device.pk]), {"command": "uname -a"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mocked.call_args.kwargs["host"], "10.0.0.5")

class ProtectedEndpointsTests(TestCase):
    def test_endpoints_redirect_anonymous_users(self):
        for name in ["network_topology_data", "network_topology", "scan_status"]:
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 302)

    @patch("monitor.views.scan_full_network")
    def test_anonymous_cannot_start_scan(self, mocked_scan):
        response = self.client.post(
            reverse("start_scan"),
            {
                "start_ip": "10.0.0.1",
                "server_type": "srv",
                "router_type": "rtr",
                "switch_type": "sw",
                "client_type": "cli",
            },
        )
        self.assertEqual(response.status_code, 302)
        mocked_scan.assert_not_called()