import json
import os
import re
from pathlib import Path
from typing import Optional

TEMPLATES_DIR = Path(os.environ.get("TEMPLATES_DIR", "/app/data/templates"))


def _ensure_dir() -> None:
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_-]+", "_", text)
    return text[:64]


def _template_path(template_id: str) -> Path:
    return TEMPLATES_DIR / f"{template_id}.json"


def list_templates() -> list[dict]:
    _ensure_dir()
    result = []
    for path in sorted(TEMPLATES_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            result.append({
                "id": data.get("id", path.stem),
                "name": data.get("name", ""),
                "description": data.get("description", ""),
                "tags": data.get("tags", []),
            })
        except (json.JSONDecodeError, OSError):
            continue
    return result


def get_template(template_id: str) -> Optional[dict]:
    path = _template_path(template_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def search_templates(query: str) -> list[dict]:
    query_lower = query.lower()
    result = []
    for tpl in list_templates():
        haystack = " ".join([
            tpl.get("name", ""),
            tpl.get("description", ""),
            " ".join(tpl.get("tags", [])),
        ]).lower()
        if query_lower in haystack:
            result.append(tpl)
    return result


def create_template(name: str, description: str, tags: list[str], code: str) -> dict:
    _ensure_dir()
    template_id = _slugify(name)
    # гарантируем уникальность id
    base_id = template_id
    counter = 1
    while _template_path(template_id).exists():
        template_id = f"{base_id}_{counter}"
        counter += 1

    data = {
        "id": template_id,
        "name": name,
        "description": description,
        "tags": tags,
        "code": code,
    }
    _template_path(template_id).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return data


def update_template(
    template_id: str,
    name: str,
    description: str,
    tags: list[str],
    code: str,
) -> Optional[dict]:
    path = _template_path(template_id)
    if not path.exists():
        return None
    data = {
        "id": template_id,
        "name": name,
        "description": description,
        "tags": tags,
        "code": code,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def delete_template(template_id: str) -> bool:
    path = _template_path(template_id)
    if not path.exists():
        return False
    path.unlink()
    return True
