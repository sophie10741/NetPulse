from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from monitor.command_builder import PARAMETER_HINTS, VALIDATORS
from monitor.models import NetworkDevice, NetworkInterface
from monitor.views import parse_keywords


class LoggedInTestCase(TestCase):
    def setUp(self):
        user = User.objects.create_user("tester", password="StrongPass123")
        self.client.force_login(user)


class HomePageTests(LoggedInTestCase):
    def test_scan_form_shown_when_no_devices(self):
        response = self.client.get("/")
        self.assertContains(response, 'name="start_ip"')
        self.assertContains(response, "Похоже, сеть ещё не отсканирована")

    def test_rescan_form_available_when_devices_exist(self):
        NetworkDevice.objects.create(name="hq-rtr", device_type="router")
        response = self.client.get("/")
        self.assertContains(response, 'name="start_ip"')
        self.assertContains(response, "Пересканировать")
        self.assertNotContains(response, "Похоже, сеть ещё не отсканирована")

    def test_device_row_has_ssh_link(self):
        device = NetworkDevice.objects.create(name="hq-srv", device_type="server")
        response = self.client.get("/")
        self.assertContains(response, reverse("ssh_command", args=[device.pk]))

    def test_status_is_taken_from_device(self):
        NetworkDevice.objects.create(name="hq-srv", device_type="server", status="offline")
        response = self.client.get("/")
        self.assertContains(response, "status--offline")
        self.assertNotContains(response, "status--online")

    def test_filter_without_matches_keeps_page(self):
        NetworkDevice.objects.create(name="hq-srv", device_type="server")
        response = self.client.get("/", {"name": "zzz"})
        self.assertContains(response, "Нет подходящих устройств")
        self.assertContains(response, 'id="topology-data"')
        self.assertNotContains(response, "Похоже, сеть ещё не отсканирована")

    def test_device_name_cannot_break_out_of_script(self):
        NetworkDevice.objects.create(name="</script><b>x", device_type="server")
        response = self.client.get("/")
        self.assertNotContains(response, "</script><b>x")


class KeywordParsingTests(SimpleTestCase):
    def test_strips_spaces_and_drops_empty_items(self):
        self.assertEqual(parse_keywords(" srv , ,file,"), ["srv", "file"])

    def test_empty_string_gives_empty_list(self):
        self.assertEqual(parse_keywords(""), [])


class StartScanValidationTests(LoggedInTestCase):
    def _post(self, **overrides):
        data = {
            "start_ip": "10.0.0.1",
            "server_type": "srv",
            "router_type": "rtr",
            "switch_type": "sw",
            "client_type": "cli",
        }
        data.update(overrides)
        return self.client.post(reverse("start_scan"), data, follow=True)

    @patch("monitor.views.scan_full_network")
    def test_empty_keywords_are_rejected(self, mocked_scan):
        response = self._post(router_type=" , ")
        self.assertContains(response, "Заполните все поля")
        mocked_scan.assert_not_called()

    @patch("monitor.views.scan_full_network")
    def test_invalid_ip_is_rejected(self, mocked_scan):
        response = self._post(start_ip="not-an-ip")
        self.assertContains(response, "Некорректный IP-адрес")
        mocked_scan.assert_not_called()


class ExecuteTemplateFormTests(LoggedInTestCase):
    def test_password_is_not_echoed_back(self):
        device = NetworkDevice.objects.create(name="hq-srv", device_type="server")
        NetworkInterface.objects.create(
            device=device, interface_name="eth0",
            mac_address="aa:bb:cc:dd:ee:ff", ip_address="10.0.0.5",
        )
        url = reverse("execute_template", args=[device.pk]) + "?template=create_user"
        response = self.client.post(
            url, {"username": "alice", "uid": "1", "password": "S3cret-Value"}
        )
        self.assertContains(response, 'value="alice"')
        self.assertNotContains(response, "S3cret-Value")


class ParameterHintsTests(SimpleTestCase):
    def test_every_validated_parameter_has_a_hint(self):
        self.assertEqual(set(VALIDATORS), set(PARAMETER_HINTS))
