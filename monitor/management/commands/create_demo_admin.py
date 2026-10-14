import os
import secrets

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Создаёт демо-администратора, если суперпользователей ещё нет"

    def handle(self, *args, **options):
        User = get_user_model()
        if User.objects.filter(is_superuser=True).exists():
            return

        username = os.environ.get("NETPULSE_ADMIN_USER") or "admin"
        password = os.environ.get("NETPULSE_ADMIN_PASSWORD") or secrets.token_urlsafe(12)
        User.objects.create_superuser(username, password=password)
        self.stdout.write(self.style.SUCCESS(f"Создан администратор: {username} / {password}"))
