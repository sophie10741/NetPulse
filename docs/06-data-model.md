# NetPulse: модель данных

Версия 1.0, октябрь 2026. Модель построена по текущему коду (`monitor/models.py`), а не по пояснительной записке.

## 1. ER-диаграмма

ER-диаграмма показывает таблицы базы и связи между ними. Запись `||--o{` читается как «один ко многим»:
например, у одного устройства может быть много интерфейсов.

```mermaid
erDiagram
    NetworkDevice ||--o{ NetworkInterface : "имеет"
    NetworkDevice ||--o{ Connection : "источник связи"
    NetworkDevice ||--o{ Connection : "цель связи"
    NetworkInterface }o..o{ MacConnection : "связана по MAC (без внешнего ключа)"
    Category ||--o{ Utility : "содержит"
    User ||--o{ Note : "автор"
    User ||--o{ Comment : "автор"
    Note ||--o{ Comment : "комментарии"
    User ||--|| Profile : "профиль"

    NetworkDevice {
        int id PK
        string name
        string device_type
        string ssh_username
        string status
        datetime last_updated
    }
    NetworkInterface {
        int id PK
        int device_id FK
        string interface_name
        string ip_address
        string mac_address
    }
    Connection {
        int id PK
        int source_id FK
        int target_id FK
    }
    MacConnection {
        int id PK
        string mac_address_device_1
        string mac_address_device_2
        datetime connection_time
    }
    Category {
        int id PK
        string name UK
        text description
    }
    Utility {
        int id PK
        int category_id FK
        string title
        text description
        text content
        datetime created_at
    }
    Note {
        int id PK
        int author_id FK
        string title
        text content
        datetime created_at
        datetime updated_at
    }
    Comment {
        int id PK
        int note_id FK
        int author_id FK
        text content
        datetime created_at
    }
    Profile {
        int id PK
        int user_id FK
        string phone_number
    }
    User {
        int id PK
        string username
        string email
    }
```

`User` — встроенная модель Django (`auth_user`); показаны только используемые поля.

## 2. Что хранится в таблицах

### Устройства и сеть

| Таблица | Поле | Описание |
|---------|------|----------|
| NetworkDevice | name | Имя хоста, полученное при сканировании |
| | device_type | router, server, client, switch или unknown; определяется по ключевым словам в имени |
| | ssh_username | Пользователь для SSH, по умолчанию root |
| | status | online или offline (проверка ping) |
| | last_updated | Время последнего сохранения |
| NetworkInterface | device | Устройство-владелец (при удалении устройства интерфейсы удаляются) |
| | interface_name | Например, eth0 |
| | ip_address | IPv4, может быть пустым |
| | mac_address | MAC в формате xx:xx:xx:xx:xx:xx |
| Connection | source, target | Два устройства, между которыми есть связь; направление отражает лишь порядок обнаружения |
| MacConnection | mac_address_device_1, _2 | Служебная таблица сканера: пары MAC-адресов, увиденных соседями. По ней строятся записи Connection |

У устройства нет столбца IP-адреса: свойство `ip_address` берёт адрес первого интерфейса, у которого он задан.

### Справочник, заметки, пользователи

| Таблица | Поля |
|---------|------|
| Category | name (уникальное), description |
| Utility («полезность») | category, title, description, content (команды и таблицы), created_at |
| Note | author, title, content, created_at, updated_at |
| Comment | note, author, content, created_at |
| Profile | user, phone_number (одна запись на пользователя, создаётся автоматически) |

## 3. Правила целостности

| Правило | Как обеспечивается |
|---------|--------------------|
| Устройство не дублируется при повторном сканировании | Поиск по имени (`get_or_create`) |
| Интерфейс не дублируется | Поиск по IP-адресу перед созданием |
| Связь не дублируется | Проверка пары в обоих направлениях |
| Удаление устройства удаляет его интерфейсы и связи | Каскадное удаление |
| Удаление заметки или автора удаляет комментарии | Каскадное удаление |

## 4. Что можно улучшить

- Устройства различаются по имени хоста, поэтому два узла с одинаковым именем сольются в одну запись. Надёжнее опираться на MAC-адрес.
- На IP-адрес интерфейса нет ограничения уникальности: дубли предотвращает только логика сканера.
- У `MacConnection` нет внешних ключей: сканеру проще, но могут остаться «висящие» записи.
