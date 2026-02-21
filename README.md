# MCP сервер шаблонов 1С

MCP-сервер для хранения и поиска шаблонов BSL-кода. Управление шаблонами — через веб-интерфейс.

**Поделиться проектом с другими (без установки Python):** см. [SHARE.md](SHARE.md) — минимальный набор файлов и инструкция «только Docker».

## Запуск

```bash
docker compose up -d
```

После первого запуска автоматически создаются два демо-шаблона:
- **Модуль печатной формы**
- **Отчёт СКД по таблице значений**

Шаблоны хранятся в папке `data/templates/` на хосте (Docker volume).  
Остановка: `docker compose down`.

## Веб-интерфейс

Откройте в браузере: **http://localhost:8023**

- Список шаблонов с поиском
- Создание и редактирование шаблонов (код в редакторе)
- Удаление шаблонов

## Подключение в Cursor

Сервер использует транспорт **Streamable HTTP** (не SSE). В настройках Cursor → MCP укажите сервер с явным типом транспорта:

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

Если Cursor по умолчанию пытается подключиться по SSE, он запрашивает `/sse` и получает 404 — тогда явно задайте `"type": "streamableHttp"`, чтобы использовался только Streamable HTTP.

## MCP-инструменты

| Инструмент | Описание |
|---|---|
| `list_templates()` | Список всех шаблонов (id, name, description, tags) |
| `get_template(template_id)` | Полный шаблон с кодом по id |
| `search_templates(query)` | Поиск по подстроке в названии, описании и тегах |

## Пример использования в Cursor

В чате Cursor напишите:

> Найди шаблон печатной формы и вставь код в текущий модуль

Cursor через MCP вызовет `search_templates("печатная форма")`, получит id шаблона,  
затем `get_template(id)` — и вернёт BSL-код.

## Структура проекта

```
.
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── app/
│   ├── main.py        # FastAPI + FastMCP
│   ├── storage.py     # CRUD по JSON-файлам
│   ├── seeds.py       # Начальные шаблоны
│   └── html/          # Jinja2-шаблоны веб-UI
└── data/
    └── templates/     # JSON-файлы шаблонов
```

## Добавление шаблона вручную

Создайте файл `data/templates/my_template.json`:

```json
{
  "id": "my_template",
  "name": "Мой шаблон",
  "description": "Описание",
  "tags": ["тег1", "тег2"],
  "code": "// BSL код..."
}
```

Файл подхватывается мгновенно — перезапуск контейнера не нужен.

## Выкладка на GitHub

1. Установите [Git](https://git-scm.com/), если ещё не установлен.

2. В папке проекта выполните в терминале:

   ```bash
   git init
   git add .
   git commit -m "MCP сервер шаблонов 1С: начальный коммит"
   ```

3. На [github.com](https://github.com) нажмите **New repository**. Имя репозитория — например `1c-templates-mcp`. Создавайте **без** README, .gitignore и лицензии (они уже есть в проекте).

4. Подключите удалённый репозиторий и отправьте код (подставьте свой логин и имя репо):

   ```bash
   git remote add origin https://github.com/ВАШ_ЛОГИН/1c-templates-mcp.git
   git branch -M main
   git push -u origin main
   ```

   Либо по SSH: `git@github.com:ВАШ_ЛОГИН/1c-templates-mcp.git`

Готово: репозиторий можно клонировать и запускать через `docker compose up -d`.
