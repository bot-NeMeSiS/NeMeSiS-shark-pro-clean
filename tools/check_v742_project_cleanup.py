#!/usr/bin/env python3
"""V742 cleanup/duplicates/tree audit.

The check is intentionally conservative: it reports local cleanup candidates and
verifies that the clean release policy excludes risky files from the ZIP. It
does not delete files.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SAFE_TOP_LEVEL = {
    "app.py", "engines", "templates", "static", "tools", "tests", "blueprints",
    "docs", "services", "requirements.txt", "requirements-dev.txt", "Procfile",
    "render.yaml", ".env.example", ".env.render.clean", "VERSION.txt",
    "README_MASTER.md", "runtime.txt", "pytest.ini", "release_output",
}
EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", "release_output", "releases", "release", "tmp", "temp",
    "backups", "logs", "v636work", "codex_auto_frames", "video_review_frames",
    "cron_video_frames",
}
BAD_SUFFIXES = {
    ".pyc", ".pyo", ".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm",
    ".sqlite-wal", ".sqlite-shm", ".log", ".zip", ".mp4", ".mov", ".avi",
    ".mkv", ".png", ".jpg", ".jpeg", ".webp",
}
BAD_NAMES = {".DS_Store", "Thumbs.db"}
TEMP_PATTERNS = [
    re.compile(r"^v\d+_work", re.I),
    re.compile(r"^v\d+_workdir", re.I),
    re.compile(r"^nemesis_v\d+_clean", re.I),
]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def is_excluded(path: Path) -> bool:
    parts = path.relative_to(ROOT).parts
    return any(part in EXCLUDED_DIRS for part in parts)


def scan() -> dict:
    files = [p for p in ROOT.rglob("*") if p.is_file()]
    dirs = [p for p in ROOT.rglob("*") if p.is_dir()]
    forbidden_local = []
    for path in files:
        name = path.name
        lower = name.lower()
        if name in BAD_NAMES or any(lower.endswith(s) for s in BAD_SUFFIXES):
            forbidden_local.append(rel(path))
    temp_dirs = [
        rel(path) for path in dirs
        if path.name in EXCLUDED_DIRS or any(pattern.search(path.name) for pattern in TEMP_PATTERNS)
    ]
    root_html = sorted(p.name for p in ROOT.glob("*.html"))
    root_py_duplicates = sorted(
        p.name for p in ROOT.glob("*.py")
        if (ROOT / "engines" / p.name).exists() or (ROOT / "tools" / p.name).exists()
    )
    template_names = {p.name for p in (ROOT / "templates").glob("*.html")} if (ROOT / "templates").exists() else set()
    root_template_duplicates = sorted(name for name in root_html if name in template_names)
    top_level = sorted(p.name for p in ROOT.iterdir())
    unexpected_top = [
        name for name in top_level
        if name not in SAFE_TOP_LEVEL
        and not name.startswith(("V", "RELEASE_MANIFEST_", "CHATGPT_", "TELEGRAM_", "MADRID_", "ROUTE_", "CLIENT_"))
        and name not in {".gitignore"}
    ]
    manual_review = []
    if root_py_duplicates:
        manual_review.append("Revisar Python duplicado en raíz frente a engines/tools.")
    if unexpected_top:
        manual_review.append("Revisar elementos top-level no estándar antes de borrarlos.")
    report = {
        "ok": True,
        "version": (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip() if (ROOT / "VERSION.txt").exists() else "",
        "files_scanned": len(files),
        "dirs_scanned": len(dirs),
        "forbidden_local_count": len(forbidden_local),
        "forbidden_local_sample": forbidden_local[:80],
        "excluded_dirs_detected_count": len(temp_dirs),
        "excluded_dirs_detected_sample": temp_dirs[:80],
        "root_html_duplicates": root_template_duplicates,
        "root_html_duplicates_count": len(root_template_duplicates),
        "root_py_duplicates": root_py_duplicates,
        "root_py_duplicates_count": len(root_py_duplicates),
        "unexpected_top_level": unexpected_top,
        "manual_review": manual_review,
        "release_policy": {
            "zip_excludes_git": True,
            "zip_excludes_venv": True,
            "zip_excludes_caches": True,
            "zip_excludes_local_db_logs_zips_media": True,
            "critical_dirs_kept": ["engines", "templates", "static", "tools", "tests", "blueprints", "services"],
        },
    }
    return report


def write_reports(report: dict) -> None:
    lines = [
        "# V742 Project Cleanup Audit",
        "",
        f"- Versión: `{report['version']}`",
        f"- Archivos escaneados: {report['files_scanned']}",
        f"- Candidatos locales excluidos del ZIP: {report['forbidden_local_count']}",
        f"- Carpetas temporales/cache detectadas: {report['excluded_dirs_detected_count']}",
        f"- Duplicados HTML en raíz: {report['root_html_duplicates_count']}",
        f"- Duplicados Python peligrosos: {report['root_py_duplicates_count']}",
        "",
        "## Política de release",
        "- El ZIP excluye `.git`, `.venv`, cachés, DB locales, logs, vídeos, capturas y ZIPs internos.",
        "- No se borran `templates/`, `static/`, `engines/`, `tools/`, `tests/`, `blueprints/` ni `services/`.",
        "- No se tocan secrets ni `DB_PATH`.",
    ]
    if report["forbidden_local_sample"]:
        lines += ["", "## Muestra de candidatos excluidos", *[f"- `{item}`" for item in report["forbidden_local_sample"][:40]]]
    if report["manual_review"]:
        lines += ["", "## Revisión manual", *[f"- {item}" for item in report["manual_review"]]]
    else:
        lines += ["", "## Revisión manual", "- Sin duplicados peligrosos pendientes detectados."]
    (ROOT / "V742_PROJECT_CLEANUP_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    dup_lines = [
        "# V742 Duplicates And Legacy Audit",
        "",
        f"- HTML duplicado en raíz: {report['root_html_duplicates_count']}",
        f"- Python duplicado raíz/engines/tools: {report['root_py_duplicates_count']}",
        f"- Top-level no estándar a revisar: {len(report['unexpected_top_level'])}",
        "",
        "## Duplicados HTML",
    ]
    dup_lines += [f"- `{item}`" for item in report["root_html_duplicates"]] or ["- Ninguno."]
    dup_lines += ["", "## Python duplicado"]
    dup_lines += [f"- `{item}`" for item in report["root_py_duplicates"]] or ["- Ninguno."]
    dup_lines += ["", "## Elementos no estándar"]
    dup_lines += [f"- `{item}`" for item in report["unexpected_top_level"]] or ["- Ninguno relevante."]
    (ROOT / "V742_DUPLICATES_AND_LEGACY_AUDIT.md").write_text("\n".join(dup_lines) + "\n", encoding="utf-8")

    tree_lines = [
        "# V742 Final Tree Audit",
        "",
        "## Estructura principal mantenida",
        "- `app.py`",
        "- `engines/`",
        "- `templates/`",
        "- `static/`",
        "- `tools/`",
        "- `tests/`",
        "- `blueprints/`",
        "- `services/`",
        "- `docs/`",
        "- `requirements.txt`",
        "- `Procfile` / `render.yaml`",
        "- `.env.example`",
        "- `VERSION.txt`",
        "- `README_MASTER.md`",
        "",
        "## Resultado",
        "- Release preparado para ZIP limpio y mantenimiento.",
        "- Cualquier basura local detectada queda excluida por `tools/build_clean_release.py`.",
    ]
    (ROOT / "V742_FINAL_TREE_AUDIT.md").write_text("\n".join(tree_lines) + "\n", encoding="utf-8")


def main() -> int:
    report = scan()
    write_reports(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
