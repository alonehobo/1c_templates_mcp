# MCP сервер шаблонов 1С

MCP-сервер для хранения и поиска шаблонов BSL-кода. Управление шаблонами — через веб-интерфейс с BSL Console (подсветка синтаксиса 1С).

## Запуск

```bat
run.bat
```

Скрипт собирает Docker-образ и запускает контейнер с маппингом `data/templates/` на хост.

Или вручную:

```bash
docker build -t mcp-templates .
docker run -d --name mcp-templates -p 8023:8023 \
  -v "$(pwd)/data/templates:/app/data/templates" \
  -e TEMPLATES_DIR=/app/data/templates \
  --restart unless-stopped mcp-templates
```

## Веб-интерфейс

Откройте в браузере: **http://localhost:8023**

- Список шаблонов с поиском (по названию, описанию, тегам)
- Создание и редактирование шаблонов в BSL Console (подсветка синтаксиса 1С)
- Удаление шаблонов

## Подключение в Cursor / Claude Code

Сервер использует транспорт **Streamable HTTP**. В настройках MCP укажите:

```json
{
  "mcpServers": {
    "1c-templates": {
      "type": "streamableHttp",
      "url": "http://localhost:8023/mcp"
    }
  }
}
```

## MCP-инструменты

| Инструмент | Описание |
|---|---|
| `list_templates()` | Список всех шаблонов (id, name, description, tags) |
| `get_template(template_id)` | Полный шаблон с кодом по id |
| `search_templates(query)` | Поиск по подстроке в названии, описании и тегах |

Поиск нечёткий: регистр и ё/е игнорируются, для слов длиннее 4 символов работает префиксный поиск (находит падежи).

## Пример использования в Cursor

В чате напишите:

> Найди шаблон для работы с Excel и вставь код в текущий модуль

Cursor через MCP вызовет `search_templates("excel")`, получит id шаблона, затем `get_template(id)` — и вернёт BSL-код.

## Хранилище шаблонов

Шаблоны хранятся в `data/templates/` (Docker volume, данные сохраняются при пересборке):

- `index.json` — метаданные всех шаблонов (id, name, description, tags)
- `<id>.bsl` — BSL-код каждого шаблона

### Добавление шаблона вручную

Создайте файл `data/templates/my_template.bsl` с кодом, а в `index.json` добавьте запись:

```json
{
  "my_template": {
    "id": "my_template",
    "name": "Мой шаблон",
    "description": "Описание",
    "tags": ["тег1", "тег2"]
  }
}
```

Новые `.bsl`-файлы без записи в `index.json` подхватываются автоматически при следующем обращении к списку.

## Структура проекта

```
.
├── Dockerfile
├── run.bat              # Сборка и запуск контейнера
├── app/
│   ├── main.py          # HTTP-сервер + MCP (stdlib Python, без зависимостей)
│   └── storage.py       # CRUD: index.json + .bsl файлы
└── data/
    └── templates/       # Шаблоны (volume, ~30 шаблонов в комплекте)
        ├── index.json
        └── *.bsl
```

Сервер написан на чистом stdlib Python — никакого pip, виртуальных окружений или сторонних пакетов.
