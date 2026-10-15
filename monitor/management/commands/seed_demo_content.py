"""Наполняет разделы «Полезности» и «Заметки» стартовым содержимым.

Команда идемпотентна: полезности добавляются, только если нет ни одной категории,
заметки — только если нет ни одной заметки. Запуск: python manage.py seed_demo_content
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from monitor.models import Category, Comment, Note, Utility

UTILITIES = {
    "Диагностика сети": (
        "Команды для проверки связи, адресов, маршрутов и портов.",
        [
            (
                "Проверка связи: ping, traceroute, mtr",
                "Как проверить доступность узла, путь пакетов и размер MTU.",
                """ping -c 4 8.8.8.8                    # 4 пакета, затем статистика
ping -c 4 -M do -s 1472 10.0.0.1     # проверка MTU 1500: 1472 байта данных + 28 заголовков
traceroute 8.8.8.8                   # путь пакетов по маршрутизаторам
tracepath 8.8.8.8                    # то же без прав root
mtr -rw -c 10 8.8.8.8                # отчёт: потери и задержки на каждом участке

# Если ping проходит по IP, но не по имени, проблема в DNS (см. «DNS-диагностика»).""",
            ),
            (
                "Адреса, маршруты и ARP: команда ip",
                "Просмотр и временная настройка сетевых параметров. Изменения пропадают после перезагрузки.",
                """ip -br a                            # краткий список интерфейсов и адресов
ip a                                 # подробный вывод
ip r                                 # таблица маршрутизации
ip route get 8.8.8.8                 # какой маршрут будет выбран для адреса
ip neigh                             # ARP-таблица (соседи)

sudo ip addr add 10.0.0.5/24 dev eth0
sudo ip addr del 10.0.0.5/24 dev eth0
sudo ip link set eth0 up             # или down
sudo ip route add 10.30.0.0/24 via 10.10.0.4""",
            ),
            (
                "Порты и сервисы: ss и nmap",
                "Что слушает на этом узле и что открыто на соседних. Сканируйте только свои сети.",
                """ss -tulpn                           # слушающие TCP/UDP-порты и процессы
ss -s                                # сводка по сокетам

nmap -sn 10.0.0.0/24                 # какие хосты отвечают
nmap -p 22,80,443 10.0.0.5           # конкретные порты
nmap -sV -p- 10.0.0.5                # все порты и версии сервисов (долго)""",
            ),
            (
                "DNS-диагностика: dig и nslookup",
                "Проверка разрешения имён и работы DNS-сервера.",
                """dig example.com                     # полный ответ
dig +short example.com A             # только адреса
dig @8.8.8.8 example.com MX          # запрос к конкретному серверу, записи почты
dig -x 8.8.8.8                       # обратный запрос (PTR)
nslookup example.com                 # то же через nslookup
resolvectl status                    # настройки DNS в systemd-resolved""",
            ),
        ],
    ),
    "Администрирование Linux": (
        "Службы, пользователи, SSH и планировщик задач.",
        [
            (
                "SSH: вход по ключу",
                "Настройка входа без пароля. Перед отключением паролей убедитесь, что вход по ключу работает.",
                """ssh-keygen -t ed25519 -C "my-laptop"   # создать ключ
ssh-copy-id user@host                   # скопировать публичный ключ на сервер
ssh user@host                           # проверить вход

# /etc/ssh/sshd_config
PermitRootLogin prohibit-password
PasswordAuthentication no

sudo sshd -t && sudo systemctl reload ssh   # проверить конфиг и применить
# В Ubuntu/Debian служба называется ssh, в RHEL-семействе sshd.""",
            ),
            (
                "Службы systemd и журнал",
                "Запуск, остановка и диагностика служб.",
                """systemctl status ssh
sudo systemctl restart ssh           # также start, stop, reload
sudo systemctl enable --now nginx    # включить автозапуск и запустить
systemctl list-units --type=service --state=failed

journalctl -u ssh -n 50 --no-pager   # последние 50 строк журнала службы
journalctl -f                        # следить за журналом в реальном времени""",
            ),
            (
                "Пользователи и права",
                "Создание пользователей, группы и sudo.",
                """sudo useradd -m -s /bin/bash alice  # создать пользователя с домашним каталогом
sudo passwd alice                    # задать пароль
sudo usermod -aG sudo alice          # дать sudo (Debian/Ubuntu; в RHEL группа wheel)
id alice                             # проверить группы
sudo userdel -r alice                # удалить вместе с домашним каталогом
sudo visudo                          # безопасное редактирование sudoers""",
            ),
            (
                "Планировщик cron",
                "Формат записи и примеры расписаний.",
                """# минута  час  день  месяц  день_недели  команда
*/5  *  *  *  *   /usr/local/bin/check.sh      # каждые 5 минут
0    3  *  *  1   /usr/local/bin/backup.sh     # по понедельникам в 03:00
30   2  1  *  *   /usr/local/bin/report.sh     # первого числа в 02:30

crontab -e                           # редактировать расписание
crontab -l                           # показать расписание""",
            ),
        ],
    ),
    "Справочники": (
        "Таблицы, которые постоянно нужны под рукой.",
        [
            (
                "Подсети IPv4: маски и размеры",
                "Сколько адресов и хостов в сети при разной длине префикса.",
                """Префикс  Маска              Адресов   Хостов
/30      255.255.255.252            4        2
/29      255.255.255.248            8        6
/28      255.255.255.240           16       14
/27      255.255.255.224           32       30
/26      255.255.255.192           64       62
/25      255.255.255.128          128      126
/24      255.255.255.0            256      254
/23      255.255.254.0            512      510
/22      255.255.252.0           1024     1022
/16      255.255.0.0            65536    65534

Хостов = адресов − 2 (адрес сети и broadcast). Исключения: /31 (2 хоста, RFC 3021) и /32 (один адрес).""",
            ),
            (
                "Частные и особые диапазоны IPv4",
                "Какие адреса не маршрутизируются в интернете и для чего они нужны.",
                """10.0.0.0/8          частная сеть (RFC 1918)
172.16.0.0/12        частная сеть (172.16.0.0 – 172.31.255.255)
192.168.0.0/16       частная сеть
100.64.0.0/10        общий адрес оператора (CGNAT)
169.254.0.0/16       link-local, адрес без DHCP
127.0.0.0/8          loopback (localhost)""",
            ),
            (
                "Порты популярных служб",
                "Что обычно слушает на стандартных портах.",
                """22    SSH                    53    DNS
25    SMTP                   67/68 DHCP (UDP)
80    HTTP                   123   NTP (UDP)
110   POP3                   143   IMAP
161   SNMP (UDP)             389   LDAP
443   HTTPS                  445   SMB
514   syslog (UDP)           587   SMTP (отправка почты)
636   LDAPS                  993   IMAPS
3306  MySQL/MariaDB          3389  RDP
5432  PostgreSQL             8080  HTTP (альтернативный)""",
            ),
        ],
    ),
    "Безопасность": (
        "Базовые меры защиты серверов.",
        [
            (
                "Чек-лист базовой защиты Linux-сервера",
                "Короткий список, с которого стоит начинать после установки системы.",
                """1. Обновления: sudo apt update && sudo apt upgrade (включить автоматические обновления безопасности).
2. Отдельный пользователь с sudo, вход root по SSH запрещён или только по ключу.
3. Вход по SSH-ключам, пароли отключены (см. «SSH: вход по ключу»).
4. Файрвол: открыты только нужные порты (ufw allow 22/tcp, ufw enable).
5. Лишние службы выключены: ss -tulpn покажет, что слушает на узле.
6. Журналы читаются и хранятся: journalctl, ротация логов.
7. Резервные копии проверяются восстановлением, а не только созданием.
8. Время синхронизируется (chrony), иначе журналы и сертификаты работают неверно.""",
            ),
        ],
    ),
}

NOTES = [
    (
        "Схема лабораторной сети NetPulse",
        """Лабораторный стенд состоит из шести узлов в трёх сегментах:
wan 10.10.0.0/24: isp-rtr (.2), hq-rtr (.3), br-rtr (.4)
hq-lan 10.20.0.0/24: hq-rtr (.2), hq-srv (.10), hq-cli (.20)
br-lan 10.30.0.0/24: br-rtr (.2), br-srv (.10)

Для сканирования начните с 10.20.0.2 (hq-rtr).""",
        "Ключевые слова для типов: srv, rtr, sw, cli.",
    ),
    (
        "Как работает сканирование",
        """Приложение подключается по SSH к стартовому устройству и читает имя хоста, интерфейсы (ip a) и соседей (arp -an).
Затем обходит найденных соседей и повторяет то же самое. Тип устройства определяется по ключевым словам в имени хоста.
Ограничение: ARP показывает только соседей в одном сегменте сети.""",
        "Если соседа не видно, проверьте, что между узлами был сетевой трафик: ARP-таблица хранит записи ограниченное время.",
    ),
    (
        "Что проверить после обновления стенда",
        """1. Сканирование находит все шесть устройств.
2. Команда hostname выполняется на hq-srv через интерфейс.
3. Повторное сканирование не создаёт дубликатов.
4. Тёмная тема: заметки, полезности и калькуляторы читаются.""",
        None,
    ),
]


class Command(BaseCommand):
    help = "Добавляет стартовые полезности и заметки, если соответствующие разделы пусты"

    def handle(self, *args, **options):
        created_utilities = self._seed_utilities()
        created_notes = self._seed_notes()
        self.stdout.write(f"Полезностей добавлено: {created_utilities}, заметок добавлено: {created_notes}")

    def _seed_utilities(self):
        if Category.objects.exists():
            return 0
        count = 0
        for category_name, (category_description, utilities) in UTILITIES.items():
            category = Category.objects.create(name=category_name, description=category_description)
            for title, description, content in utilities:
                Utility.objects.create(category=category, title=title, description=description, content=content)
                count += 1
        return count

    def _seed_notes(self):
        if Note.objects.exists():
            return 0
        author = get_user_model().objects.filter(is_superuser=True).order_by("id").first()
        if author is None:
            return 0
        count = 0
        for title, content, comment in NOTES:
            note = Note.objects.create(title=title, content=content, author=author)
            if comment:
                Comment.objects.create(note=note, author=author, content=comment)
            count += 1
        return count
