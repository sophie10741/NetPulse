from django.test import TestCase
from models import NetworkDevice

# Create your tests here.

device = NetworkDevice(
    name="Switch1",
    ip_address="192.168.1.10",
    mac_address="11:22:33:44:55:66",
    device_type="Switch"
)
device.save()

routers = NetworkDevice.objects.filter(device_type="Router")
for router in routers:
    print(router.name, router.ip_address)


device = NetworkDevice.objects.get(name="Switch1")
device.ip_address = "192.168.1.11"
device.save()


device = NetworkDevice.objects.get(name="Switch1")
device.delete()

