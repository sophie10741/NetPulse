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


def connect_client(host, username, password=None, key_filename=None, timeout=10):
    """Открывает SSH-соединение и возвращает подключённый клиент (закрывает вызывающий).

    Если пароль не задан, используется ключ: key_filename или settings.SSH_PRIVATE_KEY_PATH.
    Хост-ключи запоминаются при первом подключении; если ключ известного хоста
    изменился, подключение отклоняется.
    """
    client = _load_client()
    try:
        client.connect(
            hostname=host,
            username=username,
            password=password or None,
            key_filename=None if password else (key_filename or settings.SSH_PRIVATE_KEY_PATH),
            timeout=timeout,
            look_for_keys=False,
            allow_agent=False,
        )
        client.save_host_keys(settings.SSH_KNOWN_HOSTS_FILE)
    except Exception:
        client.close()
        raise
    return client


def execute_ssh_command(host, username, command, private_key_path=None, timeout=10):
    """Выполняет команду на хосте по SSH и возвращает вывод или текст ошибки."""
    if not host:
        return "SSH Error: у устройства нет IP-адреса"

    client = None
    try:
        client = connect_client(host, username, key_filename=private_key_path, timeout=timeout)
        _stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        output = stdout.read().decode()
        error = stderr.read().decode()

        if error:
            return f"Error: {error}"
        return output.strip()
    except Exception as e:
        return f"SSH Error: {str(e)}"
    finally:
        if client:
            client.close()