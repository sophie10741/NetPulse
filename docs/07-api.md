# NetPulse: API

Версия 1.0, октябрь 2026.

## 1. Что есть сейчас

Приложение отдаёт HTML-страницы и несколько JSON-запросов. Описание в формате OpenAPI: [api/openapi.yaml](api/openapi.yaml).
Коллекция Postman для ручной проверки: [api/NetPulse.postman_collection.json](api/NetPulse.postman_collection.json).

| Запрос | Что делает | Кому доступен | Ответ |
|--------|------------|---------------|-------|
| POST `/login/` | Вход | Всем | JSON `{success, error?}` |
| POST `/validate_user/` | Проверка выданных учётных данных | Всем | JSON `{success, error?}` |
| POST `/complete_registration/` | Завершение регистрации | После `/validate_user/` | JSON `{success, error?}` |
| GET `/logout/` | Выход | Всем | Перенаправление |
| GET `/api/network_topology/` | Устройства и связи для схемы | Вошедшим | JSON `{nodes, edges}` |
| POST `/scan/start/` | Запуск сканирования | Вошедшим | Перенаправление |
| GET `/scan/status/` | Идёт ли сканирование | Вошедшим | JSON `{scan_in_progress}` |

Особенности:

- Вход идёт через сессию (cookie): удобно для браузера, неудобно для скриптов.
- Изменяющим запросам нужен CSRF-токен: cookie `csrftoken` и заголовок `X-CSRFToken`.
- Формат ошибок разный: у входа JSON, у сканирования перенаправление с сообщением.
- Число попыток входа не ограничено (NFR-9).

### Как посмотреть спецификацию

Вариант 1. Открыть [editor.swagger.io](https://editor.swagger.io/) и вставить содержимое `openapi.yaml`.

Вариант 2. Запустить Swagger UI в Docker, из корня репозитория:

```bash
docker run --rm -p 8081:8080 -e SWAGGER_JSON=/spec/openapi.yaml -v "$PWD/docs/api:/spec" swaggerapi/swagger-ui
```

Страница откроется на `http://localhost:8081`.

### Как проверить в Postman

1. Импортировать `NetPulse.postman_collection.json`.
2. В переменных коллекции задать `baseUrl` (например, `http://192.168.52.129:8000`), `username` и `password`.
3. Выполнить по порядку: «Получить CSRF-cookie», «Вход», затем остальные запросы. В запросах есть проверки кодов и формата ответов.

## 2. Проект REST API версии 1 (пока не сделан)

Зачем: чтобы скрипты и другие системы могли делать то же, что и интерфейс. Предполагается Django REST Framework, токены и
спецификация OpenAPI, которая генерируется из кода.

| Решение | Как |
|---------|-----|
| Вход | `POST /api/v1/auth/token/` с логином и паролем, затем заголовок `Authorization: Token <значение>` |
| Формат | JSON, даты ISO 8601 |
| Ошибки | `{"error": {"code": "...", "message": "...", "fields": {...}}}` и правильные коды HTTP |
| Списки | Постраничный вывод `?page=`, фильтры в параметрах запроса |
| Права | Роли из документа «Обзор проекта»; опасные операции только для разрешённых ролей |

| Запрос | Назначение | Требование |
|--------|------------|------------|
| POST `/api/v1/auth/token/` | Получить токен | FR-1 |
| GET `/api/v1/devices/` | Список устройств, фильтры `name`, `device_type`, `status` | FR-11 |
| GET `/api/v1/devices/{id}/` | Устройство с интерфейсами | FR-11 |
| GET `/api/v1/topology/` | Узлы и связи | FR-10 |
| POST `/api/v1/scans/` | Запустить сканирование (`start_ip`, ключевые слова); ответ 202 и идентификатор | FR-5 |
| GET `/api/v1/scans/{id}/` | Состояние (`running`, `finished`, `failed`), число найденных устройств, ошибки по узлам | FR-9 |
| GET `/api/v1/templates/` | Каталог шаблонов: ключ, описание, параметры, подсказки, пояснение | FR-13 |
| POST `/api/v1/devices/{id}/commands/` | Тело: `template`, `parameters`, `dry_run`. При `dry_run=true` возвращает команду и пояснение без выполнения | FR-14, FR-15, FR-17 |
| GET `/api/v1/audit/` | Журнал действий | FR-18 |

Пример предпросмотра команды (в интерфейсе этого пока нет, FR-17):

```http
POST /api/v1/devices/3/commands/
Authorization: Token 9d1c...
Content-Type: application/json

{"template": "change_ip", "parameters": {"ip": "10.0.0.5", "mask": "24", "interface": "eth0", "old_ip": "10.0.0.4"}, "dry_run": true}
```

```json
{
  "command": "ip addr add 10.0.0.5/24 dev eth0 && ip addr del 10.0.0.4/24 dev eth0",
  "description": "Добавляет новый адрес на интерфейс и удаляет старый",
  "executed": false
}
```

Пример ошибки проверки:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Параметры не прошли проверку",
    "fields": {"ip": "ожидается IP-адрес"}
  }
}
```

Порядок работ:

1. Журнал действий (FR-18) и причины ошибок сканирования (FR-9): общий сервисный слой для интерфейса и API.
2. Предпросмотр и подтверждение команды (FR-17).
3. Токены и ресурсы `devices`, `topology`, `scans`, `templates`, `commands`.
4. Генерация OpenAPI из кода и обновление коллекции Postman.
