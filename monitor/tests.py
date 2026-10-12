import contextlib
import io
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from monitor.models import Connection, NetworkDevice, NetworkInterface
from monitor.command_builder import VALIDATORS, build_command, extract_parameters
from monitor.command_templates import command_templates

from monitor.ssh_manager import execute_ssh_command
from monitor import network_scanner_1 as scanner
from monitor.ssh_manager import connect_client

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

class CommandBuilderTests(SimpleTestCase):
    def test_valid_change_ip(self):
        command, errors = build_command(
            command_templates["change_ip"]["command"],
            {"ip": "10.0.0.2", "mask": "24", "interface": "eth0", "old_ip": "10.0.0.1"},
        )
        self.assertEqual(errors, {})
        self.assertEqual(
            command,
            "ip addr add 10.0.0.2/24 dev eth0 && ip addr del 10.0.0.1/24 dev eth0",
        )

    def test_command_injection_is_rejected(self):
        command, errors = build_command(
            command_templates["sudo_no_auth"]["command"],
            {"username": "x' ; rm -rf / ; echo '"},
        )
        self.assertIsNone(command)
        self.assertIn("username", errors)

    def test_password_is_shell_quoted(self):
        command, errors = build_command(
            command_templates["create_user"]["command"],
            {"uid": "1001", "password": "a b; reboot", "username": "alice"},
        )
        self.assertEqual(errors, {})
        self.assertIn("'a b; reboot'", command)

    def test_uid_zero_is_rejected(self):
        _, errors = build_command(
            command_templates["create_user"]["command"],
            {"uid": "0", "password": "x", "username": "alice"},
        )
        self.assertIn("uid", errors)

    def test_missing_parameter_is_rejected(self):
        command, errors = build_command(command_templates["set_timezone"]["command"], {})
        self.assertIsNone(command)
        self.assertIn("timezone", errors)

    def test_every_template_parameter_has_validator(self):
        for name, template in command_templates.items():
            for param in extract_parameters(template["command"]):
                self.assertIn(param, VALIDATORS, f"{name}: {param}")

    def test_dhcp_template_keeps_literal_braces(self):
        template = command_templates["configure_dhcp"]["command"]
        self.assertEqual(
            extract_parameters(template),
            ["subnet", "netmask", "range_start", "range_end", "gateway", "dns_server"],
        )
        command, errors = build_command(template, {
            "subnet": "10.0.0.0", "netmask": "255.255.255.0",
            "range_start": "10.0.0.10", "range_end": "10.0.0.20",
            "gateway": "10.0.0.1", "dns_server": "8.8.8.8",
        })
        self.assertEqual(errors, {})
        self.assertIn(
            "{ range 10.0.0.10 10.0.0.20; option routers 10.0.0.1; "
            "option domain-name-servers 8.8.8.8; }",
            command,
        )


class ExecuteTemplateViewTests(TestCase):
    def setUp(self):
        user = User.objects.create_user("tester", password="StrongPass123")
        self.client.force_login(user)
        self.device = NetworkDevice.objects.create(name="HQ-SRV", device_type="server")
        NetworkInterface.objects.create(
            device=self.device, interface_name="eth0",
            mac_address="aa:bb:cc:dd:ee:ff", ip_address="10.0.0.5",
        )
        self.url = reverse("execute_template", args=[self.device.pk]) + "?template=sudo_no_auth"

    @patch("monitor.views.execute_ssh_command")
    def test_invalid_parameter_does_not_reach_ssh(self, mocked):
        response = self.client.post(self.url, {"username": "x'; id; '"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("username", response.context["errors"])
        mocked.assert_not_called()

    @patch("monitor.views.execute_ssh_command", return_value="ok")
    def test_valid_parameter_runs_command(self, mocked):
        self.client.post(self.url, {"username": "alice"})
        mocked.assert_called_once()
        self.assertIn("alice", mocked.call_args.kwargs["command"])

class SshManagerTests(SimpleTestCase):
    @patch("monitor.ssh_manager._load_client")
    def test_uses_key_from_settings(self, mocked_load):
        client = mocked_load.return_value
        stdout, stderr = MagicMock(), MagicMock()
        stdout.read.return_value = b"ok\n"
        stderr.read.return_value = b""
        client.exec_command.return_value = (None, stdout, stderr)

        with self.settings(SSH_PRIVATE_KEY_PATH="/tmp/test_key"):
            result = execute_ssh_command("10.0.0.5", "root", "uname -a")

        self.assertEqual(result, "ok")
        self.assertEqual(client.connect.call_args.kwargs["key_filename"], "/tmp/test_key")
        client.close.assert_called_once()

    def test_missing_host_returns_message(self):
        self.assertIn("нет IP-адреса", execute_ssh_command(None, "root", "id"))

        class FakeSshClient:
            """Подмена SSH-клиента: отдаёт заранее заданный вывод команд."""

            def __init__(self, outputs):
                self.outputs = outputs
                self.closed = False

            def exec_command(self, command, timeout=None):
                stdout = MagicMock()
                stdout.read.return_value = self.outputs[command].encode()
                return None, stdout, MagicMock()

            def close(self):
                self.closed = True

        def _ip_a(ip, mac):
            return (
                "1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536\n"
                "    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00\n"
                "    inet 127.0.0.1/8 scope host lo\n"
                "2: eth0@if5: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500\n"
                f"    link/ether {mac} brd ff:ff:ff:ff:ff:ff\n"
                f"    inet {ip}/24 scope global eth0\n"
            )

        class SshConnectTests(SimpleTestCase):
            @patch("monitor.ssh_manager._load_client")
            def test_password_login_does_not_use_key(self, mocked_load):
                client = mocked_load.return_value
                connect_client("10.0.0.5", "root", password="secret")
                kwargs = client.connect.call_args.kwargs
                self.assertEqual(kwargs["password"], "secret")
                self.assertIsNone(kwargs["key_filename"])

        class ScannerParsingTests(SimpleTestCase):
            def test_interfaces_are_parsed_with_own_mac(self):
                client = FakeSshClient({"ip a": _ip_a("172.17.0.2", "02:42:ac:11:00:02")})
                self.assertEqual(
                    scanner.get_interfaces_via_ssh(client),
                    [
                        {"interface": "lo", "ip": "127.0.0.1", "mac": ""},
                        {"interface": "eth0", "ip": "172.17.0.2", "mac": "02:42:ac:11:00:02"},
                    ],
                )

            def test_interfaces_error_returns_empty_list(self):
                client = MagicMock()
                client.exec_command.side_effect = Exception("boom")
                self.assertEqual(scanner.get_interfaces_via_ssh(client), [])

            def test_arp_skips_incomplete_entries(self):
                client = FakeSshClient({
                    "arp -a": (
                        "router.lab (10.0.0.1) at 02:42:ac:11:00:03 [ether] on eth0\n"
                        "? (10.0.0.9) at <incomplete> on eth0\n"
                    )
                })
                self.assertEqual(
                    scanner.get_arp_via_ssh(client),
                    [{"ip": "10.0.0.1", "mac": "02:42:ac:11:00:03", "interface": "eth0"}],
                )

            def test_device_type_by_hostname(self):
                args = (["srv"], ["rtr"], ["sw"], ["cli"])
                self.assertEqual(scanner.determine_device_type("HQ-RTR", *args), "router")
                self.assertEqual(scanner.determine_device_type("hq-srv", *args), "server")
                self.assertEqual(scanner.determine_device_type("printer", *args), "unknown")

        class ScannerFullScanTests(TestCase):
            def test_two_hosts_are_scanned_and_linked(self):
                clients = {
                    "10.0.0.1": FakeSshClient({
                        "hostname": "hq-rtr\n",
                        "ip a": _ip_a("10.0.0.1", "02:00:00:00:00:01"),
                        "arp -a": "? (10.0.0.2) at 02:00:00:00:00:02 [ether] on eth0\n",
                    }),
                    "10.0.0.2": FakeSshClient({
                        "hostname": "hq-srv\n",
                        "ip a": _ip_a("10.0.0.2", "02:00:00:00:00:02"),
                        "arp -a": "? (10.0.0.1) at 02:00:00:00:00:01 [ether] on eth0\n",
                    }),
                }
                with patch(
                        "monitor.network_scanner_1.connect_client",
                        side_effect=lambda host, *args, **kwargs: clients[host],
                ):
                    scanner.scan_full_network("10.0.0.1", ["srv"], ["rtr"], ["sw"], ["cli"])

                self.assertEqual(NetworkDevice.objects.get(name="hq-rtr").device_type, "router")
                self.assertEqual(NetworkDevice.objects.get(name="hq-srv").device_type, "server")
                self.assertEqual(NetworkInterface.objects.count(), 2)
                link = Connection.objects.get()
                self.assertEqual((link.source.name, link.target.name), ("hq-rtr", "hq-srv"))
                self.assertTrue(all(c.closed for c in clients.values()))