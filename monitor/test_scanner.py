from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase

from monitor import network_scanner_1 as scanner
from monitor.models import Connection, NetworkDevice, NetworkInterface
from monitor.ssh_manager import connect_client


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