import os
import re
from queue import Queue

from monitor.models import NetworkDevice, NetworkInterface, Connection, MacConnection
from monitor.ssh_manager import connect_client

SSH_USERNAME = os.environ.get("NETPULSE_SSH_USER", "root")
SSH_PASSWORD = os.environ.get("NETPULSE_SSH_PASSWORD", "")


def _run(client, command):
    """Выполняет команду на устройстве и возвращает её вывод."""
    _stdin, stdout, _stderr = client.exec_command(command, timeout=10)
    return stdout.read().decode()


def get_hostname_via_ssh(client):
    try:
        hostname = _run(client, "hostname").strip()
        return hostname if hostname else "Unknown"
    except Exception as e:
        print(f"⚠️ Ошибка команды hostname: {e}")
        return "Unknown"


def determine_device_type(hostname, server_type, router_type, switch_type, client_type):
    hostname_lower = hostname.lower()

    if any(pattern.lower() in hostname_lower for pattern in server_type):
        return "server"
    elif any(pattern.lower() in hostname_lower for pattern in router_type):
        return "router"
    elif any(pattern.lower() in hostname_lower for pattern in switch_type):
        return "switch"
    elif any(pattern.lower() in hostname_lower for pattern in client_type):
        return "client"

    return "unknown"


def get_interfaces_via_ssh(client):
    current_interface = ""
    mac = ""
    interfaces = []

    try:
        output_ip_a = _run(client, "ip a").strip()

        for line in output_ip_a.split("\n"):
            header = re.match(r"\d+: ([^@:]+)", line)
            if header:  # Найден новый интерфейс
                current_interface = header.group(1)
                mac = ""
            elif "link/ether" in line and current_interface:
                mac_match = re.search(r"link/ether ([\da-fA-F:]+)", line)
                if mac_match:
                    mac = mac_match.group(1)
            elif "inet " in line and current_interface:  # Найден IP-адрес
                match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)/\d+", line)
                if match:
                    interfaces.append({"interface": current_interface, "ip": match.group(1), "mac": mac})
    except Exception as e:
        print(f"⚠️ Ошибка команды 'ip a': {e}")
        return []

    print(interfaces)
    return interfaces


def get_arp_via_ssh(client):
    neighbors = []

    try:
        output_arp = _run(client, "arp -a")
        print(f"📋 Вывод arp -a:\n{output_arp}")

        # Разбираем вывод arp -a
        for line in output_arp.split("\n"):
            match = re.search(r"(\S+) \(([\d.]+)\) at ([\w:<>]+) \[.*\] on (\S+)", line)
            if match:
                _neighbor_hostname, neighbor_ip, neighbor_mac, neighbor_interface = match.groups()

                # Пропускаем, если MAC-адрес отсутствует (<incomplete>)
                if neighbor_mac == "<incomplete>":
                    continue

                neighbors.append({
                    "ip": neighbor_ip,
                    "mac": neighbor_mac,
                    "interface": neighbor_interface
                })

    except Exception as e:
        print(f"⚠️ Ошибка выполнения 'arp -a': {e}")

    return neighbors


def add_to_db_device(hostname, device_type):
    """ Добавляет устройство в БД, если его там еще нет. """
    NetworkDevice.objects.get_or_create(
        name=hostname,
        defaults={"device_type": device_type, "status": "online", "ssh_username": "root"}
    )


def add_to_db_interface(ip, mac, name_device, interface_name):
    device = NetworkDevice.objects.get(name=f"{name_device}")

    interface = NetworkInterface.objects.filter(ip_address=ip).first()

    #TODO обработка существующих записей (актуализация)

    # Добавляем интерфейс, если он еще не записан
    if not interface:
        NetworkInterface.objects.create(
            device=device,
            interface_name=interface_name,
            ip_address=ip,
            mac_address=mac
        )
        print(f"✅ Добавлен интерфейс {interface_name} для {name_device} ({ip})")


def add_to_db_connection(source_device_name, source_int, target_mac):
    """ Добавляет связь между двумя устройствами, если они напрямую связаны (по MAC). """
    source_device_id = get_device_id(source_device_name)
    if source_device_id is None:
        return

    source_mac = get_mac_via_int(source_device_id, source_int)
    if not source_mac:
        return

    if not MacConnection.objects.filter(mac_address_device_1=f"{source_mac}", mac_address_device_2=f"{target_mac}").exists():
        if not MacConnection.objects.filter(mac_address_device_2=f"{source_mac}", mac_address_device_1=f"{target_mac}").exists():
            MacConnection.objects.create(mac_address_device_1=f"{source_mac}", mac_address_device_2=f"{target_mac}")
            print(f"🔗 Добавлена связь: {source_mac} → {target_mac}")
            return
    print(f"⚠️ Связь {source_mac} → {target_mac} уже существует")


def add_to_db_device_connections():
    connections = MacConnection.objects.all()

    for connection in connections:
        source_device = get_device_via_mac(connection.mac_address_device_1)
        target_device = get_device_via_mac(connection.mac_address_device_2)

        if source_device == "":
            print(f"⚠️ Ошибка: устройство с id <-{source_device}-> не найдено в БД!")
            continue

        if target_device == "":
            print(f"⚠️ Ошибка: устройство с id <-{target_device}-> не найдено в БД!")
            continue

        if source_device == target_device:
            print(f"⚠️ Пропускаем: <-{source_device}-> уже связан с самим собой.")
            continue

        if not Connection.objects.filter(source=source_device, target=target_device).exists():
            Connection.objects.create(source=source_device, target=target_device)
            print(f"🔗 Добавлена связь: {source_device} → {target_device}")
        else:
            print(f"⚠️ Связь {source_device} → {target_device} уже существует")


def get_mac_via_int(device_id, device_interface):
    interface = NetworkInterface.objects.filter(device=device_id, interface_name=str(device_interface)).first()
    if interface:
        return str(interface.mac_address)
    print(f"⚠️ MAC-адрес интерфейса {device_interface} не найден.")
    return ""


def get_device_id(device_name):
    device = NetworkDevice.objects.filter(name=f"{device_name}").first()
    if device:
        return int(device.id)
    print(f"Устройство с именем {device_name} не найдено.")
    return None


def get_device_via_mac(mac_address):
    interface = NetworkInterface.objects.filter(mac_address=mac_address).first()
    if interface:
        return interface.device
    print(f"Устройство с mac адресом {mac_address} не найдено.")
    return ""


def scan_full_network(start_ip, server_type, router_type, switch_type, client_type):
    """ Запускает полное сканирование сети с BFS. """
    print("🌍 Запускаем полное сканирование сети...")

    queue = Queue()
    scanned_ips = set()

    queue.put(start_ip)

    while not queue.empty():
        ip = queue.get()

        if ip in scanned_ips:
            continue

        try:
            client = connect_client(ip, SSH_USERNAME, password=SSH_PASSWORD or None, timeout=5)
        except Exception as e:
            print(f"⚠️ Ошибка подключения к {ip}: {e}")
            scanned_ips.add(str(ip))
            continue

        try:
            print(f"🚀 Сканируем с устройства {ip}")

            # Получаем имя хоста и добавляем устройство
            current_hostname = get_hostname_via_ssh(client)
            device_type = determine_device_type(current_hostname, server_type, router_type, switch_type, client_type)
            add_to_db_device(current_hostname, device_type)

            # Добавляем интерфейсы устройства
            for current_interface in get_interfaces_via_ssh(client):
                if current_interface["ip"] not in scanned_ips and current_interface["interface"] != "lo":
                    scanned_ips.add(str(current_interface["ip"]))
                    add_to_db_interface(
                        current_interface["ip"],
                        current_interface["mac"],
                        current_hostname,
                        current_interface["interface"]
                    )

            # Запрашиваем соседей через ARP-таблицу устройства
            neighbors = get_arp_via_ssh(client)
        finally:
            client.close()

        scanned_ips.add(str(ip))

        #TODO пересмотреть способ добавления соседей/связей.
        # Возможно, стоит создать отдельную таблицу чисто с названиями устройств (без сетевых адаптеров)

        for neighbor in neighbors:
            if neighbor["ip"] not in scanned_ips:
                # Добавляем соседа в очередь для дальнейшего сканирования
                queue.put(neighbor["ip"])

                # Добавляем связь между текущим устройством и соседом
                add_to_db_connection(current_hostname, neighbor["interface"], neighbor["mac"])

    add_to_db_device_connections()
    print("✅ Сканирование завершено!")