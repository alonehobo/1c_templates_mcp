#!/usr/bin/env python3
"""MCP-сервер шаблонов 1С. Без внешних зависимостей — только stdlib Python."""

import json
import mimetypes
import urllib.parse
import uuid
from html import escape
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

import storage

BSL_CONSOLE_DIR = Path("/app/bsl_console")

# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

CSS = """\
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f5f6f8;color:#1a1a2e;min-height:100vh}
header{background:#1a1a2e;color:#fff;padding:0 2rem;height:56px;display:flex;align-items:center;gap:1rem;position:sticky;top:0;z-index:100}
header a{color:#fff;text-decoration:none;font-weight:600;font-size:1.1rem}
header a:hover{color:#a78bfa}
header .spacer{flex:1}
.container{max-width:960px;margin:2rem auto;padding:0 1rem}
.wide{max-width:none;margin:1rem 2rem;padding:0}
.card{background:#fff;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.08);padding:1.5rem;margin-bottom:1rem}
.btn{display:inline-flex;align-items:center;gap:.4rem;padding:.45rem 1rem;border-radius:6px;font-size:.875rem;font-weight:500;cursor:pointer;text-decoration:none;border:none;transition:opacity .15s}
.btn:hover{opacity:.85}
.btn-primary{background:#6d28d9;color:#fff}
.btn-secondary{background:#e5e7eb;color:#374151}
.btn-danger{background:#dc2626;color:#fff}
.btn-sm{padding:.3rem .7rem;font-size:.8rem}
input[type=text],input[type=search],textarea{width:100%;padding:.55rem .75rem;border:1px solid #d1d5db;border-radius:6px;font-size:.9rem;font-family:inherit;outline:none;transition:border-color .15s}
input:focus,textarea:focus{border-color:#6d28d9}
label{display:block;font-size:.85rem;font-weight:500;margin-bottom:.3rem;color:#374151}
.tag{display:inline-block;background:#ede9fe;color:#5b21b6;border-radius:4px;padding:.15rem .5rem;font-size:.75rem;font-weight:500;margin-right:.3rem}
.tpl-name{font-size:1rem;font-weight:600}
.tpl-desc{color:#6b7280;font-size:.875rem;margin-top:.25rem}
.tpl-footer{display:flex;align-items:center;gap:.5rem;margin-top:.9rem;flex-wrap:wrap}
.search-row{display:flex;gap:.5rem;margin-bottom:1.25rem}
.search-row input{flex:1}
.error-box{background:#fee2e2;color:#991b1b;border:1px solid #fca5a5;border-radius:6px;padding:.75rem 1rem;margin-bottom:1rem;font-size:.875rem}
.empty{text-align:center;color:#9ca3af;padding:3rem 0}
.page-title{font-size:1.3rem;font-weight:700;margin-bottom:1.25rem}"""


def _page(title, body, header_actions="", wide=False):
    cls = "container wide" if wide else "container"
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(title)}</title>
<style>{CSS}</style>
</head>
<body>
<header>
  <a href="/">1С Шаблоны</a>
  <span class="spacer"></span>
  {header_actions}
</header>
<div class="{cls}">{body}</div>
</body>
</html>"""


def _render_index(items, q=""):
    clear = ' <a href="/" class="btn btn-secondary">✕</a>' if q else ""
    html = f'''<form method="get" action="/" class="search-row">
<input type="search" name="q" value="{escape(q)}" placeholder="Поиск по названию, описанию, тегам…">
<button type="submit" class="btn btn-secondary">Найти</button>{clear}</form>'''
    if not items:
        msg = f'Ничего не найдено по запросу «{escape(q)}»' if q else 'Шаблонов пока нет. <a href="/new">Создайте первый!</a>'
        html += f'<div class="empty">{msg}</div>'
    else:
        for t in items:
            tid = escape(t["id"])
            tags = "".join(f'<span class="tag">{escape(x)}</span>' for x in t.get("tags", []))
            desc = f'<div class="tpl-desc">{escape(t["description"])}</div>' if t.get("description") else ""
            html += f'''<div class="card">
<div class="tpl-name"><a href="/{tid}" style="color:inherit;text-decoration:none">{escape(t["name"])}</a></div>{desc}
<div class="tpl-footer">{tags}<span style="flex:1"></span>
<a href="/{tid}/edit" class="btn btn-secondary btn-sm">Редактировать</a>
<form method="post" action="/{tid}/delete" style="display:inline" onsubmit="return confirm('Удалить?')">
<button type="submit" class="btn btn-danger btn-sm">Удалить</button></form></div></div>'''
    hdr = '<a href="/" class="btn btn-secondary btn-sm">Перечитать</a> <a href="/new" class="btn btn-primary btn-sm">+ Новый шаблон</a>'
    return _page("1С Шаблоны", html, header_actions=hdr)


def _render_view(tpl):
    tid = escape(tpl["id"])
    tags = "".join(f'<span class="tag">{escape(x)}</span>' for x in tpl.get("tags", []))
    desc = f' <span style="color:#6b7280;font-size:.875rem">{escape(tpl["description"])}</span>' if tpl.get("description") else ""
    tags_html = f" <div>{tags}</div>" if tags else ""
    code_json = json.dumps(tpl.get("code", ""))
    body = f'''<div style="display:flex;align-items:baseline;gap:1rem;margin-bottom:.75rem;flex-wrap:wrap">
<div class="page-title" style="margin-bottom:0">{escape(tpl["name"])}</div>{desc}{tags_html}</div>
<div class="card" style="padding:0;overflow:hidden">
<div style="display:flex;justify-content:space-between;align-items:center;padding:.5rem 1rem;background:#f9fafb;border-bottom:1px solid #e5e7eb">
<span style="font-size:.8rem;color:#6b7280;font-weight:500">Код BSL</span></div>
<iframe id="editor" src="/bsl_console/index.html" style="width:100%;height:calc(100vh - 160px);border:none"></iframe></div>
<script>
const CODE={code_json};
const iframe=document.getElementById('editor');
iframe.onload=function(){{const w=iframe.contentWindow;
if(w.updateText){{w.updateText(CODE);w.setReadOnly(true)}}
else{{const i=setInterval(()=>{{if(w.updateText){{w.updateText(CODE);w.setReadOnly(true);clearInterval(i)}}}},100)}}}};
function copyCode(){{const w=iframe.contentWindow;const t=w.getText?w.getText():CODE;
navigator.clipboard.writeText(t).then(()=>{{const b=document.getElementById('copyBtn');b.textContent='Скопировано!';setTimeout(()=>b.textContent='Копировать',1500)}})}}
</script>'''
    hdr = f'<a href="/" class="btn btn-secondary btn-sm">К списку</a> <button onclick="copyCode()" class="btn btn-secondary btn-sm" id="copyBtn">Копировать</button> <a href="/{tid}/edit" class="btn btn-primary btn-sm">Редактировать</a>'
    return _page(f"{tpl['name']} — 1С Шаблоны", body, header_actions=hdr, wide=True)


def _render_edit(tpl=None, error=None):
    is_new = tpl is None
    title = "Новый шаблон" if is_new else f"Редактировать: {tpl['name']}"
    action = "/new" if is_new else f"/{escape(tpl['id'])}/edit"
    code = tpl.get("code", "") if tpl else ""
    code_json = json.dumps(code)
    err = f'<div class="error-box">{escape(error)}</div>' if error else ""
    body = f'''{err}<div class="page-title">{escape(title)}</div>
<form method="post" action="{action}" id="tplForm">
<div style="display:flex;gap:1rem;margin-bottom:1rem;flex-wrap:wrap">
<div style="flex:2;min-width:200px"><label for="name">Название *</label>
<input type="text" id="name" name="name" required value="{escape(tpl['name'] if tpl else '')}" placeholder="Например: Модуль печатной формы"></div>
<div style="flex:2;min-width:200px"><label for="description">Описание</label>
<input type="text" id="description" name="description" value="{escape(tpl.get('description','') if tpl else '')}" placeholder="Краткое описание назначения шаблона"></div>
<div style="flex:1;min-width:150px"><label for="tags">Теги <span style="font-weight:400;color:#9ca3af">(через запятую)</span></label>
<input type="text" id="tags" name="tags" value="{escape(', '.join(tpl.get('tags',[])) if tpl else '')}" placeholder="печать, форма, макет"></div></div>
<label>Код BSL</label>
<textarea id="code" name="code" style="display:none">{escape(code)}</textarea>
<iframe id="editor" src="/bsl_console/index.html" style="width:100%;height:calc(100vh - 200px);border:1px solid #d1d5db;border-radius:6px"></iframe></form>
<script>
const CODE={code_json};const iframe=document.getElementById('editor');
const codeArea=document.getElementById('code');const form=document.getElementById('tplForm');
iframe.onload=function(){{const w=iframe.contentWindow;
if(w.updateText){{w.updateText(CODE)}}
else{{const i=setInterval(()=>{{if(w.updateText){{w.updateText(CODE);clearInterval(i)}}}},100)}}}};
form.addEventListener('submit',function(){{const w=iframe.contentWindow;if(w.getText){{codeArea.value=w.getText()}}}});
</script>'''
    hdr = '<a href="/" class="btn btn-secondary btn-sm">К списку</a> <button type="submit" form="tplForm" class="btn btn-primary btn-sm">Сохранить</button>'
    return _page(f"{title} — 1С Шаблоны", body, header_actions=hdr, wide=True)


# ---------------------------------------------------------------------------
# MCP Protocol (JSON-RPC 2.0 over Streamable HTTP)
# ---------------------------------------------------------------------------

MCP_TOOLS = [
    {
        "name": "list_templates",
        "description": "Возвращает список всех шаблонов кода 1С (id, name, description, tags).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_template",
        "description": "Возвращает шаблон 1С по его id, включая исходный код (поле code).",
        "inputSchema": {
            "type": "object",
            "properties": {"template_id": {"type": "string"}},
            "required": ["template_id"],
        },
    },
    {
        "name": "search_templates",
        "description": "Ищет шаблоны 1С по ключевым словам в названии, описании и тегах.",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
]


def _mcp_handle(body: dict) -> dict | None:
    method = body.get("method", "")
    params = body.get("params", {})
    rid = body.get("id")

    if method == "initialize":
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": "2025-03-26",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "1c-templates", "version": "1.0.0"},
        }}

    if method in ("notifications/initialized", "notifications/cancelled"):
        return None

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": MCP_TOOLS}}

    if method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments", {})
        if name == "list_templates":
            data = storage.list_templates()
        elif name == "get_template":
            data = storage.get_template(args.get("template_id", ""))
            if data is None:
                data = {"error": f"Шаблон '{args.get('template_id', '')}' не найден"}
        elif name == "search_templates":
            data = storage.search_templates(args.get("query", ""))
        else:
            return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"Unknown tool: {name}"}}
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}],
        }}

    if method == "ping":
        return {"jsonrpc": "2.0", "id": rid, "result": {}}

    if rid is not None:
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"Method not found: {method}"}}
    return None


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):

    def _send(self, code, ctype, body):
        raw = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self._cors()
        self.end_headers()
        self.wfile.write(raw)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Expose-Headers", "Mcp-Session-Id")

    def _redirect(self, url):
        self.send_response(303)
        self.send_header("Location", url)
        self._cors()
        self.end_headers()

    def _html(self, html, code=200):
        self._send(code, "text/html; charset=utf-8", html)

    def _read_body(self):
        n = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(n) if n else b""

    def _parse_form(self):
        return dict(urllib.parse.parse_qsl(self._read_body().decode("utf-8"), keep_blank_values=True))

    # --- routes ---

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            qs = dict(urllib.parse.parse_qsl(parsed.query))

            if path.startswith("/bsl_console/"):
                self._serve_static(path)
            elif path == "/":
                q = qs.get("q", "")
                items = storage.search_templates(q) if q else storage.list_templates()
                self._html(_render_index(items, q))
            elif path == "/new":
                self._html(_render_edit())
            elif path.endswith("/edit"):
                tid = urllib.parse.unquote(path[1:].rsplit("/", 1)[0])
                tpl = storage.get_template(tid)
                self._html(_render_edit(tpl)) if tpl else self._redirect("/")
            elif path.count("/") == 1:
                tid = urllib.parse.unquote(path[1:])
                tpl = storage.get_template(tid)
                self._html(_render_view(tpl)) if tpl else self._redirect("/")
            else:
                self._send(404, "text/plain", "Not found")
        except Exception as exc:
            self._send(500, "text/plain; charset=utf-8", f"Internal error: {exc}")

    def do_POST(self):
        try:
            path = urllib.parse.urlparse(self.path).path.rstrip("/") or "/"

            if path == "/mcp":
                raw = self._read_body()
                try:
                    body = json.loads(raw)
                except (json.JSONDecodeError, ValueError):
                    self._send(400, "application/json", '{"error":"Invalid JSON"}')
                    return
                resp = _mcp_handle(body)
                if resp is None:
                    self._send(202, "text/plain", "")
                else:
                    accept = self.headers.get("Accept", "")
                    if "text/event-stream" in accept:
                        sse = f"event: message\ndata: {json.dumps(resp, ensure_ascii=False)}\n\n"
                        self._send(200, "text/event-stream", sse)
                    else:
                        self._send(200, "application/json", json.dumps(resp, ensure_ascii=False))
                return

            if path == "/new":
                form = self._parse_form()
                name = form.get("name", "").strip()
                if not name:
                    self._html(_render_edit(error="Название не может быть пустым"), 422)
                    return
                tags = [t.strip() for t in form.get("tags", "").split(",") if t.strip()]
                storage.create_template(name, form.get("description", "").strip(), tags, form.get("code", ""))
                self._redirect("/")
            elif path.endswith("/edit"):
                tid = urllib.parse.unquote(path[1:].rsplit("/", 1)[0])
                form = self._parse_form()
                name = form.get("name", "").strip()
                if not name:
                    tpl = storage.get_template(tid)
                    self._html(_render_edit(tpl, error="Название не может быть пустым"), 422)
                    return
                tags = [t.strip() for t in form.get("tags", "").split(",") if t.strip()]
                storage.update_template(tid, name, form.get("description", "").strip(), tags, form.get("code", ""))
                self._redirect("/")
            elif path.endswith("/delete"):
                tid = urllib.parse.unquote(path[1:].rsplit("/", 1)[0])
                storage.delete_template(tid)
                self._redirect("/")
            else:
                self._send(404, "text/plain", "Not found")
        except Exception as exc:
            self._send(500, "text/plain; charset=utf-8", f"Internal error: {exc}")

    def do_DELETE(self):
        path = urllib.parse.urlparse(self.path).path.rstrip("/")
        if path == "/mcp":
            self._send(200, "text/plain", "")
        else:
            self._send(404, "text/plain", "Not found")

    def _serve_static(self, path):
        rel = path[len("/bsl_console/"):]
        fp = (BSL_CONSOLE_DIR / rel).resolve()
        if not str(fp).startswith(str(BSL_CONSOLE_DIR.resolve())) or not fp.is_file():
            self._send(404, "text/plain", "Not found")
            return
        mime = mimetypes.guess_type(str(fp))[0] or "application/octet-stream"
        self._send(200, mime, fp.read_bytes())

    def log_message(self, fmt, *args):
        pass  # тишина


if __name__ == "__main__":
    storage.migrate_if_needed()
    server = ThreadingHTTPServer(("0.0.0.0", 8023), Handler)
    print("1C Templates MCP: http://0.0.0.0:8023")
    server.serve_forever()
