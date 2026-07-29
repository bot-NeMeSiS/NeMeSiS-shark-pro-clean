"""Automatización diaria para trabajar con Codex sin ensuciar el proyecto."""
from __future__ import annotations

import json
import os
import zipfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from engines.madrid_time_engine import madrid_conversion_selftest

TZ = ZoneInfo("Europe/Madrid")


FORBIDDEN_DIRS = {".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules", "logs", "backups", "v636work", "release", "release_output", "releases"}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo", ".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm", ".log", ".zip", ".mp4", ".mov", ".avi", ".mkv"}
SECRET_MARKERS = ("secret", "token", "api_key", "apikey", "private_key", "authorization", "id_rsa")


def now_label() -> str:
    return datetime.now(TZ).strftime("%Y%m%d_%H%M")


def project_version(root: Path) -> str:
    version_file = root / "VERSION.txt"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8", errors="replace").strip().lstrip("\ufeff")
    return "unknown"


def classify_path(path: Path, root: Path) -> dict:
    rel = path.relative_to(root).as_posix()
    parts = set(path.relative_to(root).parts)
    lower = rel.lower()
    lower_name = path.name.lower()
    size = path.stat().st_size if path.exists() and path.is_file() else 0
    if parts & FORBIDDEN_DIRS or any(lower.endswith(s) for s in FORBIDDEN_SUFFIXES) or path.name in {".DS_Store", "Thumbs.db"}:
        return {"path": rel, "size": size, "category": "BASURA_SEGURA", "reason": "caché, entorno, base local, log, zip o artefacto temporal", "action": "excluir del ZIP; borrar solo con purge --apply", "risk": "bajo", "auto_delete": True}
    allowed_env_examples = {".env.example", ".env.render.clean", "env.example"}
    if path.name not in allowed_env_examples and (any(marker in lower_name for marker in SECRET_MARKERS) or lower_name == ".env"):
        return {"path": rel, "size": size, "category": "PELIGROSO", "reason": "posible secreto/credencial", "action": "excluir siempre y revisar manualmente", "risk": "alto", "auto_delete": False}
    necessary_roots = {"templates", "static", "engines", "services", "blueprints", "tools", "tests", "docs", "reports"}
    necessary_files = {"app.py", "database_manager.py", "requirements.txt", "requirements-dev.txt", "VERSION.txt", ".gitignore", "render.yaml", "Procfile", "runtime.txt", "pytest.ini", "README_MASTER.md", "CODEX_DAILY_AUTOMATION_GUIDE.md", "CHATGPT_CONTINUATION_REPORT.md", "RELEASE_MANIFEST_V723.json"}
    if path.name in necessary_files or (path.relative_to(root).parts and path.relative_to(root).parts[0] in necessary_roots):
        return {"path": rel, "size": size, "category": "NECESARIO", "reason": "archivo/carpeta activo del proyecto", "action": "conservar", "risk": "bajo", "auto_delete": False}
    return {"path": rel, "size": size, "category": "DUDOSO_REVISAR", "reason": "no clasificado como producción ni basura segura", "action": "revisar manualmente", "risk": "medio", "auto_delete": False}

def audit_tree(root: Path) -> dict:
    files = [p for p in root.rglob("*") if p.is_file()]
    items = [classify_path(p, root) for p in files]
    by_category: dict[str, int] = {}
    for item in items:
        by_category[item["category"]] = by_category.get(item["category"], 0) + 1
    folders: dict[str, int] = {}
    for p in files:
        top = p.relative_to(root).parts[0] if p.relative_to(root).parts else "."
        folders[top] = folders.get(top, 0) + p.stat().st_size
    return {
        "root": str(root),
        "version": project_version(root),
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "total_files": len(files),
        "total_size_bytes": sum(p.stat().st_size for p in files),
        "by_category": by_category,
        "counts": by_category,
        "largest_folders": sorted([{"folder": k, "path": k, "size": v} for k, v in folders.items()], key=lambda x: x["size"], reverse=True)[:12],
        "largest_files": sorted(items, key=lambda x: x["size"], reverse=True)[:20],
        "forbidden": [i for i in items if i["category"] == "PELIGROSO"],
        "safe_trash": [i for i in items if i["category"] == "BASURA_SEGURA"],
        "review": [i for i in items if i["category"] == "DUDOSO_REVISAR"],
        "items": items,
    }


def data_memory_block(root: Path) -> dict:
    app_text = (root / "app.py").read_text(encoding="utf-8", errors="replace") if (root / "app.py").exists() else ""
    engine_exists = (root / "engines" / "data_memory_engine.py").exists()
    tables = ["api_sync_runs", "match_snapshots", "odds_memory_snapshots", "live_memory_snapshots", "pick_decisions", "pick_discards", "telegram_delivery_memory", "team_identity_cache", "data_memory_errors"]
    present = {table: table in app_text or (engine_exists and table in (root / "engines" / "data_memory_engine.py").read_text(encoding="utf-8", errors="replace")) for table in tables}
    return {
        "engine_exists": engine_exists,
        "admin_route": "/admin/data-memory" in app_text,
        "tables": present,
        "recommendation": "Data Memory está preparado; revisar admin/data-memory tras Daily Run real." if engine_exists else "Crear engines/data_memory_engine.py antes de avanzar con memoria SHARK.",
    }


def latest_zip(root: Path) -> Path | None:
    candidates = []
    for directory in (root.parent / "releases", root / "release_output", root):
        if directory.exists():
            candidates.extend(directory.glob("*.zip"))
    zips = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)
    return zips[0] if zips else None


def zip_status(root: Path) -> dict:
    z = latest_zip(root)
    if not z:
        return {"available": False, "exists": False, "ok": False, "message": "No hay ZIP en raíz."}
    bad = []
    count = 0
    with zipfile.ZipFile(z) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            count += 1
            lower = info.filename.lower()
            parts = set(Path(info.filename).parts)
            if parts & FORBIDDEN_DIRS or any(lower.endswith(s) for s in FORBIDDEN_SUFFIXES) or ".env" in parts:
                bad.append(info.filename)
    return {"available": True, "exists": True, "ok": not bad, "name": z.name, "zip": z.name, "files": count, "forbidden": bad[:50], "size": z.stat().st_size}


def release_zip_status(root: Path) -> dict:
    z = latest_zip(root)
    if not z:
        return {"available": False, "exists": False, "ok": False, "message": "No hay ZIP Render Ready."}
    bad = []
    count = 0
    with zipfile.ZipFile(z) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            count += 1
            lower = info.filename.lower()
            parts = set(Path(info.filename).parts)
            if parts & FORBIDDEN_DIRS or any(lower.endswith(s) for s in FORBIDDEN_SUFFIXES) or lower.endswith(".zip") or ".env" in parts:
                bad.append(info.filename)
    zips_in_project = sorted(p.name for p in root.glob("*.zip"))
    return {"available": True, "exists": True, "ok": not bad and not zips_in_project, "name": z.name, "zip": z.name, "path": str(z), "outside_project": root not in z.parents, "zip_in_project": zips_in_project, "files": count, "forbidden": bad[:50], "size": z.stat().st_size}


def active_modules_status(root: Path) -> dict:
    app_text = (root / "app.py").read_text(encoding="utf-8", errors="replace") if (root / "app.py").exists() else ""
    return {
        "telegram_football_only": "telegram_sport_filter_engine" in app_text,
        "pro_calibration": "telegram_pro_calibration" in app_text,
        "picks_quality": (root / "engines" / "picks_quality_engine.py").exists(),
        "shark_advisor": "/shark" in app_text,
        "team_identity": (root / "engines" / "team_identity_engine.py").exists(),
        "data_memory": (root / "engines" / "data_memory_engine.py").exists(),
        "visual_pro": (root / "static" / "app.css").exists(),
        "release_cleaner": (root / "tools" / "build_clean_release.py").exists(),
    }


def timezone_status() -> dict:
    selftest = madrid_conversion_selftest()
    return {"engine": "engines/madrid_time_engine.py", "timezone": "Europe/Madrid", "selftest_ok": selftest.get("ok"), "cases": selftest.get("cases", [])}


def cleanliness_status(audit: dict) -> dict:
    forbidden = len(audit.get("forbidden", []))
    trash = len(audit.get("safe_trash", []))
    review = len(audit.get("review", []))
    score = max(0, 100 - forbidden * 8 - min(trash, 50) - min(review, 30))
    if forbidden:
        status = "REVISAR"
    elif trash or review:
        status = "CONTROLADO"
    else:
        status = "LIMPIO"
    return {"score": score, "status": status}


def deliverables_status(root: Path) -> dict:
    names = [
        "V723_CODEX_AUTOMATION_TOTAL_PURGE_RELEASE_SYSTEM_REPORT.md",
        "V723_TOTAL_PURGE_AUDIT_REPORT.md",
        "CODEX_DAILY_AUTOMATION_GUIDE.md",
        "RELEASE_MANIFEST_V723.json",
        "CHATGPT_CONTINUATION_REPORT.md",
    ]
    status = {name: (root / name).exists() for name in names}
    status["reports/CODEX_DAILY_PROMPT_CURRENT.txt"] = (root / "reports" / "CODEX_DAILY_PROMPT_CURRENT.txt").exists()
    return status

def recommendations(root: Path, audit: dict | None = None) -> list[str]:
    audit = audit or audit_tree(root)
    recs = []
    if audit.get("forbidden"):
        recs.append("Revisar archivos peligrosos antes de subir a GitHub/Render.")
    if audit.get("safe_trash"):
        recs.append("Ejecutar python tools/purge_project_safe.py --dry-run y luego --apply si todo es seguro.")
    zstatus = zip_status(root)
    if not zstatus.get("ok"):
        recs.append("Generar ZIP con python tools/build_clean_release.py y auditarlo.")
    if not (root / "requirements.txt").read_text(encoding="utf-8", errors="replace").lower().count("pytest"):
        recs.append("Añadir pytest a requirements.txt para validación completa.")
    memory = data_memory_block(root)
    if not memory["engine_exists"] or not memory["admin_route"]:
        recs.append("Revisar Data Memory V721: engine o panel admin no detectado.")
    recs.append("Validar compileall, smoke_check, Cron 403/200 y runtime-version antes de cada entrega.")
    return recs


def build_daily_report(root: Path) -> dict:
    audit = audit_tree(root)
    clean = cleanliness_status(audit)
    return {
        "version": project_version(root),
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "audit": audit,
        "cleanliness": {
            "total_files": audit["total_files"],
            "safe_trash": len(audit["safe_trash"]),
            "forbidden": len(audit["forbidden"]),
            "review": len(audit["review"]),
            "score": clean["score"],
            "status": clean["status"],
        },
        "zip": release_zip_status(root),
        "active_modules": active_modules_status(root),
        "timezone": timezone_status(),
        "data_memory": data_memory_block(root),
        "deliverables": deliverables_status(root),
        "telegram_cron_checklist": [
            "/api/runtime-version correcto",
            "telegram/tick sin secret -> 403",
            "telegram/tick con secret -> 200",
            "daily/run sin secret -> 403",
            "daily/run con secret -> 200",
            "JSON Cron compacto",
            "Admin diagnostics con detalle largo",
        ],
        "recommendations": recommendations(root, audit),
    }


def prompt_from_report(report: dict) -> str:
    recs = "\n".join(f"- {item}" for item in report.get("recommendations", []))
    return f"""Estoy continuando NeMeSiS SHARK PRO desde la versión {report.get('version')}.

Reglas:
- No rehacer la app.
- No romper Render, Telegram automático, Cron, DB_PATH=/data/database.db, AUTOMATION_SECRET, login, admin, cliente, membresías, SHARK, picks, combis hasta 15 ni Data Memory.
- No tocar ni mostrar secrets reales.
- Entregar siempre ZIP limpio Render Ready.

Estado:
- Archivos totales: {report['cleanliness']['total_files']}
- Basura segura detectada: {report['cleanliness']['safe_trash']}
- Peligrosos detectados: {report['cleanliness']['forbidden']}
- ZIP: {report['zip'].get('zip', 'no disponible')} | OK: {report['zip'].get('ok')} | fuera del proyecto: {report['zip'].get('outside_project')}
- ZIPs en raiz del proyecto: {report['zip'].get('zip_in_project', [])}
- Hora Madrid: {report['timezone'].get('timezone')} | selftest: {report['timezone'].get('selftest_ok')}
- Modulos activos: Telegram football-only, calibracion PRO, calidad picks, SHARK Advisor, Team Identity, Data Memory, Visual PRO y Release Cleaner.
- Data Memory engine: {report['data_memory']['engine_exists']} | admin: {report['data_memory']['admin_route']}
- Render/Cron: no mostrar secrets; validar 403 sin secret y 200 con secret en tick/daily.
- Telegram: revisar ultimo tick/daily, enviados hoy, descartados y errores desde admin diagnostics.

Próximos objetivos recomendados:
{recs}

Validación obligatoria:
- python -m py_compile app.py
- python -m compileall -q .
- python tools/check_madrid_times.py
- python tools/nemesis_daily_codex.py
- python tools/smoke_check.py
- python tools/build_clean_release.py
- python tools/audit_release_zip.py
- python tools/validate_release.py
- pytest -q si pytest está instalado
"""


def write_daily_outputs(root: Path) -> dict:
    reports = root / "reports"
    reports.mkdir(exist_ok=True)
    label = now_label()
    report = build_daily_report(root)
    prompt = prompt_from_report(report)
    md = reports / f"CODEX_DAILY_REPORT_{label}.md"
    js = reports / f"CODEX_DAILY_REPORT_{label}.json"
    current = reports / "CODEX_DAILY_PROMPT_CURRENT.txt"
    md.write_text(render_daily_markdown(report, prompt), encoding="utf-8")
    js.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    current.write_text(prompt, encoding="utf-8")
    return {"report": report, "markdown": str(md), "json": str(js), "prompt": str(current)}


def render_daily_markdown(report: dict, prompt: str) -> str:
    recs = "\n".join(f"- {item}" for item in report.get("recommendations", []))
    return f"""# Codex Daily Automation

Versión: `{report.get('version')}`

Generado: `{report.get('generated_at')}`

## Limpieza

- Archivos: {report['cleanliness']['total_files']}
- Basura segura: {report['cleanliness']['safe_trash']}
- Peligrosos: {report['cleanliness']['forbidden']}
- Revisar manualmente: {report['cleanliness']['review']}

## ZIP

- Disponible: {report['zip'].get('available')}
- OK: {report['zip'].get('ok')}
- Archivo: {report['zip'].get('zip', '-')}
- Fuera del proyecto: {report['zip'].get('outside_project')}
- ZIPs en raíz del proyecto: {report['zip'].get('zip_in_project', [])}

## Hora Madrid

- Engine: {report['timezone'].get('engine')}
- Selftest: {report['timezone'].get('selftest_ok')}

## Módulos activos

{json.dumps(report.get('active_modules', {}), ensure_ascii=False, indent=2)}

## Memoria SHARK

- Engine: {report['data_memory']['engine_exists']}
- Admin: {report['data_memory']['admin_route']}
- Recomendación: {report['data_memory']['recommendation']}

## Recomendaciones

{recs}

## Prompt actual

```text
{prompt}
```
"""
