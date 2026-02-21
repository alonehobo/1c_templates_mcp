import os
from pathlib import Path

from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates
from starlette.routing import Route
from mcp.server.fastmcp import FastMCP

import storage

# ---------------------------------------------------------------------------
# MCP-сервер
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "1c-templates",
    stateless_http=True,
    json_response=True,
)


@mcp.tool()
def list_templates() -> list[dict]:
    """Возвращает список всех шаблонов кода 1С (id, name, description, tags)."""
    return storage.list_templates()


@mcp.tool()
def get_template(template_id: str) -> dict | None:
    """Возвращает шаблон 1С по его id, включая исходный код (поле code)."""
    tpl = storage.get_template(template_id)
    if tpl is None:
        return {"error": f"Шаблон '{template_id}' не найден"}
    return tpl


@mcp.tool()
def search_templates(query: str) -> list[dict]:
    """Ищет шаблоны 1С по ключевым словам в названии, описании и тегах."""
    return storage.search_templates(query)


# ---------------------------------------------------------------------------
# Веб-UI обработчики
# ---------------------------------------------------------------------------

HTML_DIR = Path(__file__).parent / "html"
templates = Jinja2Templates(directory=str(HTML_DIR))


async def index(request: Request):
    q = request.query_params.get("q", "")
    if q:
        items = storage.search_templates(q)
    else:
        items = storage.list_templates()
    return templates.TemplateResponse(
        request, "index.html", {"items": items, "q": q}
    )


async def new_form(request: Request):
    return templates.TemplateResponse(
        request, "edit.html", {"tpl": None, "error": None}
    )


async def new_save(request: Request):
    form = await request.form()
    name = form.get("name", "")
    description = form.get("description", "")
    tags = form.get("tags", "")
    code = form.get("code", "")
    
    if not name.strip():
        return templates.TemplateResponse(
            request, "edit.html",
            {"tpl": None, "error": "Название не может быть пустым"},
            status_code=422,
        )
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    storage.create_template(name.strip(), description.strip(), tag_list, code)
    return RedirectResponse("/", status_code=303)


async def edit_form(request: Request):
    template_id = request.path_params["template_id"]
    tpl = storage.get_template(template_id)
    if tpl is None:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        request, "edit.html", {"tpl": tpl, "error": None}
    )


async def edit_save(request: Request):
    template_id = request.path_params["template_id"]
    form = await request.form()
    name = form.get("name", "")
    description = form.get("description", "")
    tags = form.get("tags", "")
    code = form.get("code", "")
    
    if not name.strip():
        tpl = storage.get_template(template_id)
        return templates.TemplateResponse(
            request, "edit.html",
            {"tpl": tpl, "error": "Название не может быть пустым"},
            status_code=422,
        )
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    storage.update_template(template_id, name.strip(), description.strip(), tag_list, code)
    return RedirectResponse("/", status_code=303)


async def delete(request: Request):
    template_id = request.path_params["template_id"]
    storage.delete_template(template_id)
    return RedirectResponse("/", status_code=303)


# ---------------------------------------------------------------------------
# Объединение веб-UI и MCP в один ASGI-процесс
# ---------------------------------------------------------------------------

def _seed_initial_templates() -> None:
    """Создаёт демо-шаблоны при первом запуске, если папка пустая."""
    from pathlib import Path as _Path
    tdir = _Path(os.environ.get("TEMPLATES_DIR", "/app/data/templates"))
    tdir.mkdir(parents=True, exist_ok=True)
    if any(tdir.glob("*.json")):
        return

    try:
        import seeds  # noqa: F401
    except ImportError:
        pass


_seed_initial_templates()

# Используем приложение MCP как основное и добавляем веб-роуты
app = mcp.streamable_http_app()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)

# Добавляем веб-UI роуты к MCP приложению
app.routes.append(Route("/", endpoint=index, methods=["GET"]))
app.routes.append(Route("/new", endpoint=new_form, methods=["GET"]))
app.routes.append(Route("/new", endpoint=new_save, methods=["POST"]))
app.routes.append(Route("/{template_id}/edit", endpoint=edit_form, methods=["GET"]))
app.routes.append(Route("/{template_id}/edit", endpoint=edit_save, methods=["POST"]))
app.routes.append(Route("/{template_id}/delete", endpoint=delete, methods=["POST"]))


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8023)
