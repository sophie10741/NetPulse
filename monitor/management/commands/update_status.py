from django.core.management.base import BaseCommand
from monitor.models import NetworkDevice

class Command(BaseCommand):
    help = 'Обновляет статусы устройств'

    def handle(self, *args, **kwargs):
        devices = NetworkDevice.objects.all()
        for device in devices:
            device.check_and_update_status()
        self.stdout.write(self.style.SUCCESS('Статусы устройств обновлены'))
