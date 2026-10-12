from django.contrib import admin
from .models import NetworkDevice, NetworkInterface, Connection
from .models import Category, Utility

class NetworkInterfaceInline(admin.TabularInline):
    model = NetworkInterface
    extra = 0
    fields = ("interface_name", "ip_address", "mac_address")
    readonly_fields = ("interface_name", "ip_address", "mac_address")

class NetworkDeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'device_type', 'status')
    search_fields = ("name", "device_type")
    inlines = [NetworkInterfaceInline]

    def is_online_display(self, obj):
        return "Online" if obj.is_online() else "Offline"
    is_online_display.short_description = "Online status"

    def get_snmp_info_display(self, obj):
        return obj.get_snmp_info()
    get_snmp_info_display.short_description = "SNMP info"
admin.site.register(NetworkDevice, NetworkDeviceAdmin)
admin.site.register(NetworkInterface)
admin.site.register(Connection)
admin.site.register(Category)
admin.site.register(Utility)
