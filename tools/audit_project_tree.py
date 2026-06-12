#!/usr/bin/env python3
"""V726 project tree audit.

Classifies every file without deleting anything. The purge tool consumes the
same classifier and only removes BASURA_SEGURA items with auto_delete=True.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"
VERSION_FILE = ROOT / "VERSION.txt"
VERSION = VERSION_FILE.read_text(encoding="utf-8-sig").strip() if VERSION_FILE.exists() else "DEV"

NECESSARY_ROOT_DIRS = {"blueprints", "docs", "engines", "services", "static", "templates", "tests", "tools", "reports", "data"}
NECESSARY_ROOT_FILES = {
    ".env.example", ".env.render.clean", ".gitignore", ".gitkeep", "__init__.py",
    "app.py", "database_manager.py", "Procfile", "pytest.ini", "README_MASTER.md",
    "render.yaml", "requirements-dev.txt", "requirements.txt", "runtime.txt", "VERSION.txt",
    "CODEX_DAILY_AUTOMATION_GUIDE.md", "CHATGPT_CONTINUATION_REPORT.md",
}
SAFE_TRASH_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "v636work"}
PROTECTED_DIRS = {".git", ".venv", "venv", "env"}
BUILD_OUTPUT_DIRS = {"release_output", "release", "releases", "dist", "build"}
SAFE_TRASH_SUFFIXES = {
    ".pyc", ".pyo", ".db-wal", ".db-shm", ".sqlite-wal", ".sqlite-shm",
    ".log", ".tmp", ".temp", ".bak",
}
LOCAL_DB_SUFFIXES = {".db", ".sqlite", ".sqlite3"}
MEDIA_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".png.tmp"}
SECRET_MARKERS = ("secret", "token", "private_key", "id_rsa", "credentials")
ALLOWED_ENV = {".env.example", ".env.render.clean", "env.example"}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def referenced_templates() -> set[str]:
    app_text = _read_text(ROOT / "app.py")
    return set(re.findall(r"render_template\(\s*['\"]([^'\"]+)['\"]", app_text))


def template_files() -> set[str]:
    return {p.name for p in (ROOT / "templates").glob("*.html")} if (ROOT / "templates").exists() else set()


def engine_files() -> set[str]:
    files = set()
    for folder in ("engines", "services", "tools", "blueprints"):
        directory = ROOT / folder
        if directory.exists():
            files.update(p.name for p in directory.glob("*.py"))
    return files


TEMPLATE_NAMES = template_files()
REFERENCED_TEMPLATES = referenced_templates()
ENGINE_NAMES = engine_files()


def category_payload(path: Path) -> dict:
    rel = path.relative_to(ROOT).as_posix()
    parts = path.relative_to(ROOT).parts
    part_set = set(parts)
    name = path.name
    lower_name = name.lower()
    lower_rel = rel.lower()
    size = path.stat().st_size if path.exists() and path.is_file() else 0

    def item(category: str, reason: str, action: str, risk: str = "bajo", auto_delete: bool = False) -> dict:
        return {
            "path": rel,
            "size": size,
            "category": category,
            "reason": reason,
            "action": action,
            "risk": risk,
            "auto_delete": auto_delete,
        }

    if part_set & PROTECTED_DIRS:
        return item("PELIGROSO_NO_PUBLICAR" if ".git" not in part_set else "DUDOSO_REVISAR", "carpeta local/protegida; excluir del ZIP", "conservar en workspace, excluir release", "alto", False)
    if path.name not in ALLOWED_ENV and (lower_name == ".env" or any(marker in lower_name for marker in SECRET_MARKERS)):
        return item("PELIGROSO_NO_PUBLICAR", "posible secreto o credencial", "revisar manualmente y excluir siempre", "alto", False)
    if part_set & SAFE_TRASH_DIRS:
        return item("BASURA_SEGURA", "cache/carpeta temporal local", "eliminar con purge --apply", "bajo", True)
    if part_set & BUILD_OUTPUT_DIRS:
        return item("DUDOSO_REVISAR", "salida de build/release; no entra en ZIP final", "conservar si contiene el release final, excluir del paquete", "medio", False)
    if any(lower_name.endswith(suffix) for suffix in SAFE_TRASH_SUFFIXES):
        return item("BASURA_SEGURA", "archivo temporal/cache generado", "eliminar con purge --apply", "bajo", True)
    if lower_name.endswith(".zip"):
        return item("BASURA_SEGURA", "ZIP interno no debe vivir dentro del proyecto", "eliminar o mover fuera del workspace", "bajo", True)
    if any(lower_name.endswith(suffix) for suffix in MEDIA_SUFFIXES):
        return item("BASURA_SEGURA", "video/captura temporal no necesaria en release", "eliminar con purge --apply", "bajo", True)
    if any(lower_name.endswith(suffix) for suffix in LOCAL_DB_SUFFIXES):
        if rel == "data/.gitkeep":
            return item("NECESARIO", "marcador de carpeta data", "conservar", "bajo", False)
        return item("BASURA_SEGURA", "base SQLite local o backup local; Render usa /data/database.db", "eliminar del workspace, nunca incluir en ZIP", "medio", True)
    if len(parts) == 1 and lower_name.endswith(".html") and name in TEMPLATE_NAMES:
        return item("DUPLICADO_LEGACY", "HTML duplicado en raíz; existe versión activa en templates/", "no borrar automático; revisar si puede archivarse", "medio", False)
    if len(parts) == 1 and lower_name.endswith(".py") and name in ENGINE_NAMES:
        return item("DUPLICADO_LEGACY", "Python duplicado en raíz; existe versión organizada en engines/services/tools/blueprints", "no borrar automático; revisar si puede archivarse", "medio", False)
    if len(parts) == 1 and (lower_name.startswith("readme_v") or lower_name.startswith("v7") or lower_name.startswith("v6") or lower_name.startswith("changelog_") or lower_name.endswith("_report.md") or lower_name.endswith("_diff.patch")):
        current = "v726" in lower_name or "v725" in lower_name or "chatgpt_continuation" in lower_name
        return item("NECESARIO" if current else "DUDOSO_REVISAR", "documentación histórica útil pero excesiva para release final" if not current else "informe actual", "mantener fuera del ZIP salvo lista blanca" if not current else "conservar", "bajo" if current else "medio", False)
    if parts and parts[0] in NECESSARY_ROOT_DIRS:
        if parts[0] == "data" and name != ".gitkeep":
            return item("BASURA_SEGURA", "dato local dentro de data; la producción usa /data/database.db", "eliminar si no es .gitkeep", "medio", True)
        return item("NECESARIO", "carpeta activa del proyecto", "conservar", "bajo", False)
    if len(parts) == 1 and name in NECESSARY_ROOT_FILES:
        return item("NECESARIO", "archivo raíz activo del proyecto", "conservar", "bajo", False)
    return item("DUDOSO_REVISAR", "archivo no clasificado como producción ni basura segura", "revisar manualmente", "medio", False)


def audit_tree(root: Path = ROOT) -> dict:
    files = [p for p in root.rglob("*") if p.is_file()]
    items = [category_payload(p) for p in files]
    counts: dict[str, int] = {}
    for entry in items:
        counts[entry["category"]] = counts.get(entry["category"], 0) + 1
    folders: dict[str, int] = {}
    for path in files:
        top = path.relative_to(root).parts[0] if path.relative_to(root).parts else "."
        folders[top] = folders.get(top, 0) + path.stat().st_size
    by_cat = {cat: [entry for entry in items if entry["category"] == cat] for cat in counts}
    return {
        "ok": True,
        "version": VERSION,
        "root": str(root),
        "total_files": len(files),
        "total_size_bytes": sum(path.stat().st_size for path in files),
        "counts": counts,
        "largest_folders": sorted([{"path": key, "size": value} for key, value in folders.items()], key=lambda x: x["size"], reverse=True)[:20],
        "largest_files": sorted(items, key=lambda x: x["size"], reverse=True)[:30],
        "necessary": by_cat.get("NECESARIO", []),
        "safe_trash": by_cat.get("BASURA_SEGURA", []),
        "duplicates": by_cat.get("DUPLICADO_LEGACY", []),
        "review": by_cat.get("DUDOSO_REVISAR", []),
        "dangerous": by_cat.get("PELIGROSO_NO_PUBLICAR", []),
        "items": items,
    }


def markdown(report: dict) -> str:
    lines = [
        "# Auditoría de árbol V726",
        "",
        f"- Versión detectada: `{report['version']}`",
        f"- Raíz: `{report['root']}`",
        f"- Archivos: {report['total_files']}",
        f"- Tamaño total: {report['total_size_bytes']} bytes",
        "",
        "## Clasificación",
    ]
    for key in ("NECESARIO", "BASURA_SEGURA", "DUPLICADO_LEGACY", "DUDOSO_REVISAR", "PELIGROSO_NO_PUBLICAR"):
        lines.append(f"- {key}: {report['counts'].get(key, 0)}")
    sections = [
        ("Basura segura", report["safe_trash"]),
        ("Duplicado / legacy", report["duplicates"]),
        ("Dudoso revisar", report["review"]),
        ("Peligroso no publicar", report["dangerous"]),
    ]
    for title, entries in sections:
        lines.extend(["", f"## {title}"])
        if not entries:
            lines.append("- Sin elementos.")
        for entry in entries[:200]:
            lines.append(f"- `{entry['path']}` · {entry['reason']} · acción: {entry['action']}")
    lines.extend(["", "## Carpetas más pesadas"])
    for entry in report["largest_folders"][:15]:
        lines.append(f"- `{entry['path']}`: {entry['size']} bytes")
    lines.extend(["", "## Archivos más pesados"])
    for entry in report["largest_files"][:15]:
        lines.append(f"- `{entry['path']}`: {entry['size']} bytes · {entry['category']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORT_DIR.mkdir(exist_ok=True)
    report = audit_tree(ROOT)
    (REPORT_DIR / "V726_PROJECT_TREE_AUDIT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = markdown(report)
    (REPORT_DIR / "V726_PROJECT_TREE_AUDIT.md").write_text(md, encoding="utf-8")
    (ROOT / "V726_PROJECT_TREE_AUDIT.md").write_text(md, encoding="utf-8")
    print(json.dumps({
        "ok": True,
        "version": report["version"],
        "total_files": report["total_files"],
        "counts": report["counts"],
        "safe_trash": len(report["safe_trash"]),
        "duplicates": len(report["duplicates"]),
        "review": len(report["review"]),
        "dangerous": len(report["dangerous"]),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
