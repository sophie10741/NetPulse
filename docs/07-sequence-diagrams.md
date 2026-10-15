# NetPulse: диаграммы последовательности

Версия 0.1, октябрь 2026. Диаграммы построены в Mermaid и отображаются на GitHub.
Они отражают реальную работу кода (модули `views`, `command_builder`, `ssh_manager`, `network_scanner_1`).

## 1. Сканирование сети

```mermaid
sequenceDiagram
    actor A as Администратор
    participant UI as Браузер
    participant V as NetPulse views
    participant S as Сканер в отдельном потоке
    participant D as Сетевое устройство
    participant DB as База данных

    A->>UI: IP старта и ключевые слова
    UI->>V: POST /scan/start/
    V->>V: проверка входа, IP-адреса и слов
    alt ввод некорректен
        V-->>UI: переход на главную + сообщение об ошибке
    else сканирование уже идёт
        V-->>UI: переход на главную
    else
        V->>S: запустить scan_full_network
        V-->>UI: переход на /scan/progress/
        par фоновый обход
            loop пока очередь не пуста
                S->>D: SSH-подключение (ключ, таймаут 5 с)
                alt подключиться не удалось
                    S->>S: пропустить узел
                else
                    S->>D: hostname, ip a, arp -an
                    D-->>S: вывод команд
                    S->>DB: устройство и интерфейсы
                    S->>S: соседи в очередь, связь по MAC
                end
            end
            S->>DB: связи между устройствами по MAC
        and опрос состояния
            loop каждые несколько секунд
                UI->>V: GET /scan/status/
                V-->>UI: scan_in_progress
            end
        end
        UI->>V: GET /
        V->>DB: устройства, интерфейсы, связи
        V-->>UI: схема и таблица
    end
```

## 2. Выполнение шаблона команды

```mermaid
sequenceDiagram
    actor A as Администратор
    participant UI as Браузер
    participant V as execute_template_view
    participant B as command_builder
    participant M as ssh_manager
    participant D as Сетевое устройство

    A->>UI: выбрать шаблон в меню устройства
    UI->>V: GET /devices/{id}/template/?template=ключ
    V->>B: extract_parameters(шаблон)
    B-->>V: список полей
    V-->>UI: форма с подсказками

    A->>UI: заполнить и отправить
    UI->>V: POST /devices/{id}/template/?template=ключ
    V->>B: build_command(шаблон, значения)
    B->>B: проверка каждого параметра
    alt есть ошибки
        B-->>V: нет команды, ошибки по полям
        V-->>UI: форма с сообщениями, значения сохранены
    else все параметры верны
        B-->>V: готовая команда
        V->>M: execute_ssh_command(host, user, command)
        M->>D: SSH (ключ из настроек, проверка известных хостов)
        D-->>M: вывод или ошибка
        M-->>V: текст результата
        V-->>UI: страница с результатом
    end

    Note over V,B: Запланировано (FR-36): перед выполнением показать итоговую команду и пояснение, запросить подтверждение
```

## 3. Первый вход пользователя

```mermaid
sequenceDiagram
    actor C as Главный администратор
    actor U as Пользователь
    participant UI as Браузер
    participant V as NetPulse views
    participant DB as База данных

    C->>DB: создать учётную запись (панель администратора)
    C-->>U: передать логин и временный пароль

    U->>UI: ввести логин и пароль
    UI->>V: POST /validate_user/
    V->>DB: проверка учётных данных
    alt данные неверны
        V-->>UI: success: false, error
    else данные верны
        V-->>UI: success: true (имя пользователя в сессии)
        U->>UI: email, телефон, новый пароль
        UI->>V: POST /complete_registration/
        alt пароли не совпадают
            V-->>UI: success: false, error
        else
            V->>DB: новый пароль, email, телефон
            V-->>UI: success: true
        end
    end
    Note over U,V: Автоматического входа нет: после завершения регистрации пользователь входит с новым паролем
```

## История изменений

| Версия | Изменение |
|--------|-----------|
| 0.1 | Три диаграммы |
