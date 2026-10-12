import re

def _init_():
    get_inerfaces_via_ssh()

def get_inerfaces_via_ssh():
    interfaces = []

    # try:
    #     client = paramiko.SSHClient()
    #     client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    #     client.connect(ip, username=SSH_USERNAME, password=SSH_PASSWORD, timeout=2)

        # stdin, stdout, stderr = client.exec_command("hostname")
        # output_ip_a = stdout.read().decode().strip()

    output_ip_a = """1: lo:  mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
2: eth0:  mtu 1500 qdisc fq_codel state UP group default qlen 1000
    link/ether 51:55:07:8a:62:44 brd ff:ff:ff:ff:ff:ff
    inet 192.168.120.24/24 brd 192.168.120.255 scope global dynamic eth0
       valid_lft 2900sec preferred_lft 2900sec
    inet6 fe80::5054:ff:fe8c:6244/64 scope link 
       valid_lft forever preferred_lft forever"""

    for line in output_ip_a.split("\n"):
        interface_match = re.search(r"^\d+: (\S+):", line)
        if interface_match:
            interface_name = interface_match.group(1)
            ip_match = re.search(r"inet (\S+)", line)
            ip_address = ip_match.group(1) if ip_match else None
            mac_match = re.search(r"link/ether (\S+)", line)
            mac_address = mac_match.group(1) if mac_match else None
            interfaces.append({
                "interface": interface_name,
                "ip": ip_address,
                "mac": mac_address
            })
        # client.close()
    print(interfaces)
    print('1')
    return interfaces if interfaces else "Unknown"
    # except Exception as e:
    #     print(f"⚠️ Ошибка подключения к {ip}: {e}")
    #     return "Unknown"