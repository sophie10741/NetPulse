"""Построение shell-команд из шаблонов с проверкой параметров."""
import ipaddress
import re
import shlex
from string import Formatter


class ParameterError(ValueError):
    """Значение параметра не прошло проверку."""


def _ip(value):
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        raise ParameterError("ожидается IP-адрес")


def _int_range(low, high):
    def check(value):
        if not re.fullmatch(r"[0-9]{1,6}", value) or not low <= int(value) <= high:
            raise ParameterError(f"ожидается число от {low} до {high}")
        return str(int(value))
    return check


def _regex(pattern, hint):
    compiled = re.compile(pattern)

    def check(value):
        if not compiled.fullmatch(value):
            raise ParameterError(hint)
        return value
    return check


def _password(value):
    if not 1 <= len(value) <= 128 or any(ch in value for ch in "\n\r\0"):
        raise ParameterError("пароль: 1–128 символов без переводов строки")
    return shlex.quote(value)


_host = _regex(r"[A-Za-z0-9.-]{1,253}", "ожидается имя хоста или IP-адрес")
_iface = _regex(r"[A-Za-z0-9_.:-]{1,15}", "ожидается имя интерфейса, например eth0")


def _hosts(value):
    tokens = [t for t in re.split(r"[,\s]+", value.strip()) if t]
    if not tokens or len(tokens) > 50:
        raise ParameterError("ожидается от 1 до 50 хостов через пробел или запятую")
    for token in tokens:
        _host(token)
    return "\\n".join(tokens)


VALIDATORS = {
    "ip": _ip, "old_ip": _ip, "gateway": _ip, "remote_ip": _ip, "local_ip": _ip,
    "subnet": _ip, "netmask": _ip, "range_start": _ip, "range_end": _ip,
    "dns_server": _ip,
    "mask": _int_range(0, 128),
    "interface": _iface, "tunnel_name": _iface,
    "uid": _int_range(1000, 60000),
    "username": _regex(r"[a-z_][a-z0-9_-]{0,31}", "ожидается имя пользователя Linux"),
    "password": _password,
    "port": _int_range(1, 65535),
    "attempts": _int_range(1, 20),
    "banner": _regex(r"[\w .,:!?()-]{1,200}", "допустимы буквы, цифры, пробел и . , : ! ? ( ) -"),
    "domain": _host, "server": _host,
    "timezone": _regex(r"[A-Za-z0-9_+/-]{1,64}", "ожидается, например, Europe/Moscow"),
    "hosts": _hosts,
}

# Подсказки для полей формы (показываются как placeholder)
PARAMETER_HINTS = {
    "ip": "Новый IP-адрес, например 10.0.0.5",
    "old_ip": "Текущий IP-адрес, который нужно убрать",
    "mask": "Длина маски, например 24",
    "interface": "Имя интерфейса, например eth0",
    "gateway": "IP-адрес шлюза",
    "remote_ip": "IP-адрес удалённой стороны туннеля",
    "local_ip": "IP-адрес этого устройства",
    "tunnel_name": "Имя туннеля, например gre1",
    "uid": "Число от 1000 до 60000",
    "username": "Например, alice",
    "password": "От 1 до 128 символов",
    "port": "Число от 1 до 65535",
    "attempts": "Число от 1 до 20",
    "banner": "Текст баннера",
    "subnet": "Адрес подсети, например 10.0.0.0",
    "netmask": "Маска, например 255.255.255.0",
    "range_start": "Начало диапазона адресов",
    "range_end": "Конец диапазона адресов",
    "dns_server": "IP-адрес DNS-сервера",
    "domain": "Например, lab.local",
    "server": "Например, pool.ntp.org",
    "timezone": "Например, Europe/Moscow",
    "hosts": "Хосты через пробел или запятую",
}


def extract_parameters(command):
    """Имена полей шаблона в порядке появления (экранированные {{ }} не считаются)."""
    names = []
    for _, field, _, _ in Formatter().parse(command):
        if field and field not in names:
            names.append(field)
    return names


def build_command(command, raw_values):
    """Проверяет значения и подставляет их в шаблон.

    Возвращает (команда, ошибки). Если есть ошибки, команда равна None.
    """
    values, errors = {}, {}
    for name in extract_parameters(command):
        validator = VALIDATORS.get(name)
        if validator is None:
            errors[name] = "неизвестный параметр шаблона"
            continue
        try:
            values[name] = validator((raw_values.get(name) or "").strip())
        except ParameterError as exc:
            errors[name] = str(exc)
    if errors:
        return None, errors
    return command.format(**values), {}
