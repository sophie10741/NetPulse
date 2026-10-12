import os

import paramiko
from django.conf import settings


def _load_client():
    client = paramiko.SSHClient()
    known_hosts = settings.SSH_KNOWN_HOSTS_FILE
    if os.path.exists(known_hosts):
        client.load_host_keys(known_hosts)
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    return client


def execute_ssh_command(host, username, command, private_key_path=None, timeout=10):
    """Выполняет команду на хосте по SSH.

    Ключ берётся из settings.SSH_PRIVATE_KEY_PATH. Хост-ключи запоминаются при первом
    подключении; если ключ известного хоста изменился, подключение отклоняется.
    """
    if not host:
        return "SSH Error: у устройства нет IP-адреса"

    client = _load_client()
    try:
        client.connect(
            hostname=host,
            username=username,
            key_filename=private_key_path or settings.SSH_PRIVATE_KEY_PATH,
            timeout=timeout,
            look_for_keys=False,
            allow_agent=False,
        )
        client.save_host_keys(settings.SSH_KNOWN_HOSTS_FILE)

        _stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        output = stdout.read().decode()
        error = stderr.read().decode()

        if error:
            return f"Error: {error}"
        return output.strip()
    except Exception as e:
        return f"SSH Error: {str(e)}"
    finally:
        client.close()