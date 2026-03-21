import json
import os
import re
from pathlib import Path
from typing import Optional

TEMPLATES_DIR = Path(os.environ.get("TEMPLATES_DIR", "/app/data/templates"))
INDEX_PATH = TEMPLATES_DIR / "index.json"


def _ensure_dir() -> None:
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_-]+", "_", text)
    return text[:64]


def _code_path(template_id: str) -> Path:
    return TEMPLATES_DIR / f"{template_id}.bsl"


# ---------------------------------------------------------------------------
# Index: единый файл метаданных
# ---------------------------------------------------------------------------

def _read_index() -> dict[str, dict]:
    """Читает index.json. Возвращает {id: {id, name, description, tags}}."""
    if not INDEX_PATH.exists():
        return {}
    try:
        data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            # совместимость: список → словарь
            return {item["id"]: item for item in data if "id" in item}
        return data
    except (json.JSONDecodeError, OSError):
        return {}


def _write_index(index: dict[str, dict]) -> None:
    _ensure_dir()
    tmp = INDEX_PATH.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(INDEX_PATH)


def _sync_bsl_files(index: dict[str, dict]) -> bool:
    """Синхронизирует индекс с .bsl файлами на диске. Возвращает True если индекс изменился."""
    changed = False
    existing_bsl = {bsl.stem for bsl in TEMPLATES_DIR.glob("*.bsl")}

    # Новые .bsl → добавляем в индекс
    for tid in existing_bsl:
        if tid not in index:
            index[tid] = {
                "id": tid,
                "name": tid.replace("_", " ").capitalize(),
                "description": "",
                "tags": [],
            }
            changed = True

    # Удалённые .bsl → убираем из индекса
    removed = [tid for tid in index if tid not in existing_bsl]
    for tid in removed:
        del index[tid]
        changed = True

    return changed


# ---------------------------------------------------------------------------
# Миграция: старые .json файлы → index.json
# ---------------------------------------------------------------------------

def migrate_if_needed() -> None:
    """Один раз переносит данные из отдельных .json в index.json."""
    _ensure_dir()
    index = _read_index()

    # Собираем метаданные из старых .json файлов
    migrated = False
    for path in TEMPLATES_DIR.glob("*.json"):
        if path.name == "index.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            tid = data.get("id", path.stem)
            if tid not in index:
                index[tid] = {
                    "id": tid,
                    "name": data.get("name", ""),
                    "description": data.get("description", ""),
                    "tags": data.get("tags", []),
                }
                migrated = True
            # Удаляем старый .json
            path.unlink()
        except (json.JSONDecodeError, OSError):
            continue

    # Подхватываем .bsl без метаданных
    if _sync_bsl_files(index):
        migrated = True

    if migrated or not INDEX_PATH.exists():
        _write_index(index)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def list_templates() -> list[dict]:
    _ensure_dir()
    index = _read_index()
    # Подхватываем новые .bsl, добавленные вручную
    if _sync_bsl_files(index):
        _write_index(index)
    return sorted(
        [
            {"id": v["id"], "name": v["name"], "description": v["description"], "tags": v["tags"]}
            for v in index.values()
        ],
        key=lambda x: x["name"].lower(),
    )


def get_template(template_id: str) -> Optional[dict]:
    index = _read_index()
    meta = index.get(template_id)
    if meta is None:
        return None
    result = {**meta}
    bsl = _code_path(template_id)
    if bsl.exists():
        result["code"] = bsl.read_text(encoding="utf-8")
    else:
        result["code"] = ""
    return result


def _normalize(text: str) -> str:
    """Нормализация для поиска: нижний регистр + ё→е."""
    return text.lower().replace("ё", "е")


def _word_matches(word: str, text: str) -> bool:
    """
    Проверяет наличие слова в тексте.
    Для слов длиннее 4 символов допускается префиксное совпадение
    (обрабатывает падежи: «коллизии» найдёт «коллизий», «коллизию» и т.д.).
    """
    if word in text:
        return True
    if len(word) > 4:
        prefix = word[:max(4, len(word) - 2)]
        return prefix in text
    return False


def search_templates(query: str) -> list[dict]:
    """
    Поиск по всем словам запроса (AND-семантика).
    - Каждое слово ищется независимо
    - Регистр и ё/е игнорируются
    - Для слов длиннее 4 символов работает префиксный поиск (падежи)
    """
    words = _normalize(query).split()
    if not words:
        return list_templates()

    results = []
    for tpl in list_templates():
        haystack = _normalize(" ".join([
            tpl.get("name", ""),
            tpl.get("description", ""),
            " ".join(tpl.get("tags", [])),
        ]))
        if all(_word_matches(w, haystack) for w in words):
            results.append(tpl)
    return results


def create_template(name: str, description: str, tags: list[str], code: str) -> dict:
    _ensure_dir()
    index = _read_index()

    template_id = _slugify(name)
    base_id = template_id
    counter = 1
    while template_id in index:
        template_id = f"{base_id}_{counter}"
        counter += 1

    meta = {
        "id": template_id,
        "name": name,
        "description": description,
        "tags": tags,
    }
    index[template_id] = meta
    _write_index(index)
    _code_path(template_id).write_text(code, encoding="utf-8")
    return {**meta, "code": code}


def update_template(
    template_id: str,
    name: str,
    description: str,
    tags: list[str],
    code: str,
) -> Optional[dict]:
    index = _read_index()
    if template_id not in index:
        return None
    meta = {
        "id": template_id,
        "name": name,
        "description": description,
        "tags": tags,
    }
    index[template_id] = meta
    _write_index(index)
    _code_path(template_id).write_text(code, encoding="utf-8")
    return {**meta, "code": code}


def delete_template(template_id: str) -> bool:
    index = _read_index()
    if template_id not in index:
        return False
    del index[template_id]
    _write_index(index)
    bsl = _code_path(template_id)
    if bsl.exists():
        bsl.unlink()
    return True
