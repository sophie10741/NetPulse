from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from monitor.models import Category, Note, Utility


class SeedDemoContentTests(TestCase):
    def _seed(self):
        call_command("seed_demo_content", stdout=StringIO())

    def test_seeds_utilities_and_notes(self):
        User.objects.create_superuser("admin", password="StrongPass123")
        self._seed()
        self.assertGreaterEqual(Category.objects.count(), 4)
        self.assertGreaterEqual(Utility.objects.count(), 10)
        self.assertGreaterEqual(Note.objects.count(), 3)

    def test_second_run_does_not_duplicate(self):
        User.objects.create_superuser("admin", password="StrongPass123")
        self._seed()
        counts = (Category.objects.count(), Utility.objects.count(), Note.objects.count())
        self._seed()
        self.assertEqual(counts, (Category.objects.count(), Utility.objects.count(), Note.objects.count()))

    def test_notes_are_skipped_without_superuser(self):
        self._seed()
        self.assertEqual(Note.objects.count(), 0)
        self.assertGreater(Utility.objects.count(), 0)


class PagesTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("tester", password="StrongPass123")
        self.client.force_login(self.user)


class UsefulPagesTests(PagesTestCase):
    def setUp(self):
        super().setUp()
        self.net = Category.objects.create(name="Сеть", description="d")
        self.linux = Category.objects.create(name="Linux", description="d")
        for i in range(6):
            Utility.objects.create(category=self.net, title=f"net-{i}", description="d", content="c")
        Utility.objects.create(category=self.linux, title="linux-1", description="d", content="ip a\nip r")

    def test_category_filter(self):
        response = self.client.get(reverse("useful"), {"category": self.linux.id})
        self.assertContains(response, "linux-1")
        self.assertNotContains(response, "net-0")

    def test_pagination_keeps_category(self):
        response = self.client.get(reverse("useful"), {"category": self.net.id})
        self.assertContains(response, f"?page=2&category={self.net.id}")

    def test_detail_shows_content_as_preformatted_text(self):
        utility = Utility.objects.get(title="linux-1")
        response = self.client.get(reverse("useful_detail", args=[utility.id]))
        self.assertContains(response, "<pre")
        self.assertContains(response, "ip a\nip r")

    def test_unknown_utility_returns_404(self):
        response = self.client.get(reverse("useful_detail", args=[9999]))
        self.assertEqual(response.status_code, 404)


class NotesTests(PagesTestCase):
    def setUp(self):
        super().setUp()
        self.note = Note.objects.create(title="Моя заметка", content="строка 1\nстрока 2", author=self.user)
        self.other = User.objects.create_user("other", password="StrongPass123")

    def test_delete_by_get_does_not_delete(self):
        self.client.get(reverse("delete_note", args=[self.note.pk]))
        self.assertTrue(Note.objects.filter(pk=self.note.pk).exists())

    def test_author_can_delete_by_post(self):
        self.client.post(reverse("delete_note", args=[self.note.pk]))
        self.assertFalse(Note.objects.filter(pk=self.note.pk).exists())

    def test_other_user_cannot_delete(self):
        self.client.force_login(self.other)
        self.client.post(reverse("delete_note", args=[self.note.pk]))
        self.assertTrue(Note.objects.filter(pk=self.note.pk).exists())

    def test_edit_buttons_only_for_author(self):
        url = reverse("note_detail", args=[self.note.pk])
        self.assertContains(self.client.get(url), reverse("edit_note", args=[self.note.pk]))
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(url), reverse("edit_note", args=[self.note.pk]))

    def test_edit_form_has_edit_title(self):
        response = self.client.get(reverse("edit_note", args=[self.note.pk]))
        self.assertContains(response, "Редактировать заметку")


class CalculatorTests(PagesTestCase):
    def test_subnet_result(self):
        response = self.client.post(reverse("subnet_calculator"), {"ip": "192.168.1.10/24"})
        self.assertContains(response, "192.168.1.1 - 192.168.1.254")
        self.assertContains(response, "254")

    def test_subnet_single_host(self):
        response = self.client.post(reverse("subnet_calculator"), {"ip": "10.0.0.5/32"})
        self.assertContains(response, "10.0.0.5 - 10.0.0.5")

    def test_subnet_error_is_shown(self):
        response = self.client.post(reverse("subnet_calculator"), {"ip": "not-an-ip"})
        self.assertContains(response, "Неверный IP-адрес или маска")

    def test_server_calculator_zero_capacity_is_an_error_not_a_crash(self):
        response = self.client.post(reverse("server_calculator"), {
            "users": "100", "cpu_per_user": "0.5", "ram_per_user": "1",
            "server_cpu": "0", "server_ram": "16",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ошибка ввода данных")

    def test_calculator_links_are_not_underlined_cards(self):
        response = self.client.get(reverse("calculators"))
        self.assertContains(response, 'class="np-tile"')
