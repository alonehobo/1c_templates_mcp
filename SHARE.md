# Минимальный набор для распространения

Чтобы поделиться проектом с другими **без установки Python и прочего ПО** — нужен только **Docker** (Docker Desktop или Docker Engine).

## Что отдать получателю

Скопируйте в архив или папку **ровно эти файлы и каталоги**:

```
Dockerfile
docker-compose.yml
requirements.txt
app/
  main.py
  storage.py
  seeds.py
  html/
    base.html
    edit.html
    index.html
data/
  templates/    ← папка может быть пустой (демо-шаблоны создадутся при первом запуске)
```

Файлы `data/templates/*.json` можно не включать — при первом запуске автоматически появятся два демо-шаблона.

## Инструкция для получателя

1. Установить [Docker](https://www.docker.com/products/docker-desktop/) (Docker Desktop для Windows/Mac или Docker Engine для Linux), если ещё не установлен.

2. Распаковать архив в любую папку, открыть в ней терминал и выполнить:

   ```bash
   docker compose up -d
   ```

3. Открыть в браузере: **http://localhost:8023**  
   — веб-интерфейс для просмотра и редактирования шаблонов.

4. *(Опционально)* Подключить MCP в Cursor: в настройках MCP добавить:

   ```json
   "1c-templates": {
     "type": "streamableHttp",
     "url": "http://localhost:8023/mcp"
   }
   ```

Остановка сервера: `docker compose down`.

---

Никакого Python, pip или виртуальных окружений устанавливать не нужно — всё работает внутри контейнера.
