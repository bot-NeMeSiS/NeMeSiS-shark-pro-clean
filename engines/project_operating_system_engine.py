"""Shared operating system for NeMeSiS development and company direction.

All information is derived from local files, Git metadata, or explicitly passed
runtime state. The engine performs no provider calls and no product DB writes.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import tempfile
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from engines.sports_platform_contracts import build_sports_platform_contract_registry


MADRID = ZoneInfo("Europe/Madrid")
OPERATING_SYSTEM_CONTRACT = "NEMESIS-COMPANY-DEVELOPER-OS-V1"

GENERATED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".cache",
    "release_output",
    "logs",
    "backups",
    "tmp",
    "v636work",
}
EVIDENCE_DIRS = {"reports", "browser_qa", "reference_images"}
DATA_DIRS = {"data"}
SOURCE_DIRS = (
    ".github",
    "automation_workforce",
    "blueprints",
    "docs",
    "engines",
    "services",
    "static",
    "templates",
    "tests",
    "tools",
)
ROOT_DOCUMENTS = {
    "README_MASTER.md",
    "NEMESIS_PRODUCT_BIBLE.md",
    "NEMESIS_SPORTS_UX_BIBLE.md",
    "NEMESIS_MATCH_CENTER_UX_BIBLE.md",
    "MATCH_CENTER_DECISION_REPORT.md",
    "MATCH_CENTER_IMPLEMENTATION_BACKLOG.md",
    "MATCH_CENTER_FOUNDATION_REPORT.md",
    "PROJECT_NEMESIS_SPORTS_EXPERIENCE_MASTER_SPECIFICATION.md",
}
ROOT_CONFIG = {
    ".gitignore",
    ".env.example",
    "env.example",
    "APP_VERSION",
    "VERSION.txt",
    "Procfile",
    "render.yaml",
    "runtime.txt",
    "pytest.ini",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-browser.txt",
    "nemesis-smoke.yml",
    "RELEASE_MANIFEST.json",
}
ARCHIVE_FORBIDDEN_SUFFIXES = {
    ".bak",
    ".db",
    ".db3",
    ".old",
    ".orig",
    ".rej",
    ".save",
    ".sqlite",
    ".sqlite3",
    ".swp",
    ".tmp",
    ".wal",
    ".shm",
    ".journal",
    ".log",
    ".zip",
    ".mp4",
    ".mov",
    ".avi",
    ".webm",
}
ARCHIVE_FORBIDDEN_NAMES = {
    ".env",
    "credentials.json",
    "service-account.json",
    "id_rsa",
    "id_dsa",
}
ARCHIVE_REQUIRED = {
    "app.py",
    "VERSION.txt",
    "requirements.txt",
    "templates/base.html",
    "static/app.css",
}


def _text(value: Any, limit: int = 300) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()[:limit]


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _is_below(path: Path, root: Path) -> bool:
    resolved = path.resolve()
    return resolved == root or root in resolved.parents


def _skip_parts(relative: Path, *, include_evidence: bool = False) -> bool:
    blocked = set(GENERATED_DIRS) | set(DATA_DIRS)
    if not include_evidence:
        blocked |= set(EVIDENCE_DIRS)
    return any(part in blocked for part in relative.parts)


def _iter_files(root: Path, *, include_evidence: bool = False) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if _skip_parts(relative, include_evidence=include_evidence):
            continue
        yield path


def _git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip()


def _safe_remote(value: str) -> str:
    remote = _text(value, 500)
    if not remote:
        return ""
    if "://" not in remote:
        return remote
    try:
        parsed = urlsplit(remote)
        hostname = parsed.hostname or ""
        netloc = hostname
        if parsed.port:
            netloc = f"{hostname}:{parsed.port}"
        return urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))
    except ValueError:
        return "remote_configured"


def _git_snapshot(root: Path) -> dict[str, Any]:
    if not (root / ".git").exists():
        render_sha = _text(os.getenv("RENDER_GIT_COMMIT"), 80)
        return {
            "state": "BLOCKED_BY_ACCESS",
            "branch": "",
            "head_sha": render_sha,
            "main_sha": "",
            "origin_main_sha": "",
            "ahead_main": None,
            "behind_main": None,
            "working_tree_clean": None,
            "remote": "",
            "summary": "El artefacto runtime no contiene metadatos Git.",
        }
    branch = _git(root, "branch", "--show-current")
    head = _git(root, "rev-parse", "HEAD")
    main = _git(root, "rev-parse", "main")
    origin_main = _git(root, "rev-parse", "origin/main")
    status = _git(root, "status", "--porcelain")
    left_right = _git(root, "rev-list", "--left-right", "--count", "main...HEAD")
    behind = ahead = None
    if left_right:
        try:
            behind, ahead = (int(value) for value in left_right.split()[:2])
        except (TypeError, ValueError):
            behind = ahead = None
    aligned = bool(head and (head == main or head == origin_main))
    state = "CONFIRMED" if aligned else "REQUIRES_REVIEW"
    return {
        "state": state,
        "branch": branch,
        "head_sha": head,
        "main_sha": main,
        "origin_main_sha": origin_main,
        "ahead_main": ahead,
        "behind_main": behind,
        "working_tree_clean": status == "",
        "remote": _safe_remote(_git(root, "remote", "get-url", "origin")),
        "summary": (
            "HEAD coincide con main."
            if aligned
            else "La carpeta actual y main contienen historiales distintos; requiere integración controlada."
        ),
    }


def _static_routes(root: Path) -> dict[str, Any]:
    route_map: dict[str, list[dict[str, str]]] = defaultdict(list)
    files = [root / "app.py"]
    blueprint_root = root / "blueprints"
    if blueprint_root.exists():
        files.extend(sorted(blueprint_root.glob("*.py")))
    parse_failures: list[str] = []
    for path in files:
        if not path.is_file():
            continue
        try:
            tree = ast.parse(_read(path))
        except SyntaxError:
            parse_failures.append(_relative(path, root))
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call) or not decorator.args:
                    continue
                function = decorator.func
                method = function.attr if isinstance(function, ast.Attribute) else ""
                first = decorator.args[0]
                if method not in {"route", "get", "post", "put", "patch", "delete"}:
                    continue
                if not isinstance(first, ast.Constant) or not isinstance(first.value, str):
                    continue
                route_map[first.value].append(
                    {
                        "file": _relative(path, root),
                        "function": node.name,
                        "decorator": method,
                    }
                )
    duplicates = {
        route: entries
        for route, entries in route_map.items()
        if len(entries) > 1
    }
    return {
        "total": sum(len(entries) for entries in route_map.values()),
        "unique": len(route_map),
        "duplicates": duplicates,
        "parse_failures": parse_failures,
    }


def _exact_source_duplicates(root: Path) -> list[dict[str, Any]]:
    candidates: list[Path] = []
    candidates.extend(path for path in root.glob("*.py") if path.name not in {"app.py", "__init__.py"})
    for directory in ("engines", "services", "blueprints", "tools", "tests"):
        base = root / directory
        if base.exists():
            candidates.extend(
                path
                for path in base.rglob("*")
                if path.is_file()
                and path.suffix.lower() in {".py", ".html", ".css", ".js"}
                and path.name != "__init__.py"
                and "__pycache__" not in path.parts
            )
    by_hash: dict[str, list[Path]] = defaultdict(list)
    for path in candidates:
        try:
            by_hash[_hash_file(path)].append(path)
        except OSError:
            continue
    groups = []
    for paths in by_hash.values():
        unique = sorted({_relative(path, root) for path in paths})
        if len(unique) < 2:
            continue
        groups.append(
            {
                "files": unique,
                "bytes": sum((root / item).stat().st_size for item in unique),
                "state": "CONFIRMED",
            }
        )
    return sorted(groups, key=lambda item: (-len(item["files"]), item["files"][0]))


def _css_quality(root: Path) -> dict[str, Any]:
    selector_files: dict[str, list[str]] = defaultdict(list)
    for path in sorted((root / "static").glob("*.css")):
        source = re.sub(r"/\*.*?\*/", "", _read(path), flags=re.S)
        for group in re.findall(r"([^{}]+)\{", source):
            if group.lstrip().startswith("@"):
                continue
            for raw in group.split(","):
                selector = " ".join(raw.split())
                if selector:
                    selector_files[selector].append(path.name)
    repeated = sum(len(files) - 1 for files in selector_files.values() if len(files) > 1)
    cross_file = {
        selector: sorted(set(files))
        for selector, files in selector_files.items()
        if len(set(files)) > 1
    }
    return {
        "files": len(list((root / "static").glob("*.css"))),
        "unique_selectors": len(selector_files),
        "repeated_occurrences": repeated,
        "cross_file_selectors": len(cross_file),
        "examples": [
            {"selector": selector, "files": files}
            for selector, files in sorted(cross_file.items())[:12]
        ],
        "state": "REQUIRES_REVIEW" if cross_file else "CONFIRMED",
        "note": "La repetición CSS puede ser cascada intencional; no se elimina sin Browser QA.",
    }


def _js_quality(root: Path) -> dict[str, Any]:
    names: dict[str, list[str]] = defaultdict(list)
    files = sorted((root / "static").glob("*.js"))
    for path in files:
        source = _read(path)
        for name in re.findall(r"\bfunction\s+([A-Za-z_$][\w$]*)\s*\(", source):
            names[name].append(path.name)
    duplicates = {
        name: sorted(set(locations))
        for name, locations in names.items()
        if len(set(locations)) > 1
    }
    return {
        "files": len(files),
        "duplicate_named_functions": duplicates,
        "state": "REQUIRES_REVIEW" if duplicates else "CONFIRMED",
    }


def _template_quality(root: Path) -> dict[str, Any]:
    paths = sorted((root / "templates").rglob("*.html"))
    by_hash: dict[str, list[str]] = defaultdict(list)
    for path in paths:
        try:
            by_hash[_hash_file(path)].append(_relative(path, root))
        except OSError:
            continue
    duplicates = [files for files in by_hash.values() if len(files) > 1]
    return {
        "files": len(paths),
        "exact_duplicate_groups": duplicates,
        "state": "REQUIRES_REVIEW" if duplicates else "CONFIRMED",
    }


def _domain_inventory(root: Path) -> list[dict[str, Any]]:
    engine_names = [path.name.lower() for path in (root / "engines").glob("*.py")]
    domains = {
        "Cliente": ("client", "membership", "navigation", "experience"),
        "Admin": ("admin", "operations", "company", "sentinel"),
        "Sports": ("sports", "match", "live", "football", "odds", "pick"),
        "SHARK": ("shark",),
        "Telegram": ("telegram",),
        "Empresa": ("company", "business", "revenue", "growth"),
        "Automatización": ("automation", "cron", "scheduler", "workforce"),
        "Seguridad": ("security", "privacy", "secret", "csrf"),
    }
    result = []
    for label, tokens in domains.items():
        matched = sorted(
            name
            for name in engine_names
            if any(token in name for token in tokens)
        )
        result.append(
            {
                "name": label,
                "modules": len(matched),
                "examples": matched[:6],
                "state": "CONFIRMED" if matched else "NOT_CERTIFIED",
            }
        )
    return result


def _dependency_inventory(root: Path) -> dict[str, Any]:
    requirements = []
    for line in _read(root / "requirements.txt").splitlines():
        value = line.strip()
        if value and not value.startswith("#"):
            requirements.append(value)
    workflows = []
    workflow_root = root / ".github" / "workflows"
    if workflow_root.exists():
        workflows = sorted(path.name for path in workflow_root.glob("*.y*ml"))
    return {
        "python": requirements,
        "python_count": len(requirements),
        "workflows": workflows,
        "render_configured": (root / "render.yaml").is_file(),
        "procfile_configured": (root / "Procfile").is_file(),
        "state": "CONFIRMED",
    }


def _file_stats(root: Path) -> dict[str, Any]:
    source_files = list(_iter_files(root))
    suffixes = Counter(path.suffix.lower() or "(none)" for path in source_files)
    evidence_files = []
    for name in EVIDENCE_DIRS:
        base = root / name
        if base.exists():
            evidence_files.extend(path for path in base.rglob("*") if path.is_file())
    return {
        "source_files": len(source_files),
        "source_bytes": sum(path.stat().st_size for path in source_files),
        "evidence_files": len(evidence_files),
        "evidence_bytes": sum(path.stat().st_size for path in evidence_files),
        "engines": len(list((root / "engines").glob("*.py"))),
        "services": len(list((root / "services").glob("*.py"))),
        "blueprints": len(list((root / "blueprints").glob("*.py"))),
        "templates": len(list((root / "templates").rglob("*.html"))),
        "css": len(list((root / "static").glob("*.css"))),
        "js": len(list((root / "static").glob("*.js"))),
        "tests": len(list((root / "tests").rglob("test_*.py"))),
        "tools": len(list((root / "tools").glob("*.py"))),
        "by_suffix": dict(suffixes.most_common(12)),
    }


def _archive_status(root: Path) -> dict[str, Any]:
    path = root / "release_output" / "NeMeSiS_DEV_SOURCE.zip"
    if not path.is_file():
        return {"available": False, "path": "", "bytes": 0, "sha256": ""}
    try:
        return {
            "available": True,
            "path": _relative(path, root),
            "bytes": path.stat().st_size,
            "sha256": _hash_file(path),
        }
    except OSError:
        return {"available": False, "path": "", "bytes": 0, "sha256": ""}


@lru_cache(maxsize=4)
def _static_snapshot(project_root: str, app_version: str) -> dict[str, Any]:
    root = Path(project_root).resolve()
    return {
        "version": app_version,
        "file_stats": _file_stats(root),
        "routes": _static_routes(root),
        "domains": _domain_inventory(root),
        "dependencies": _dependency_inventory(root),
        "quality": {
            "exact_source_duplicates": _exact_source_duplicates(root),
            "css": _css_quality(root),
            "js": _js_quality(root),
            "templates": _template_quality(root),
        },
        "sports_platform": build_sports_platform_contract_registry(root),
    }


def clear_project_snapshot_cache() -> None:
    _static_snapshot.cache_clear()


def build_product_roadmap(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()

    def complete(*files: str) -> bool:
        return all((root / file).is_file() for file in files)

    modules = [
        {
            "name": "Fundación de producto",
            "state": "COMPLETED" if complete("NEMESIS_PRODUCT_BIBLE.md", "NEMESIS_SPORTS_UX_BIBLE.md") else "PENDING",
            "evidence": "Product Bible y Sports UX Bible",
        },
        {
            "name": "Calendario deportivo",
            "state": "COMPLETED" if complete("static/v940-calendar.js", "templates/calendar.html") else "PENDING",
            "evidence": "Contrato sports-metrics-v1 y experiencia V940",
        },
        {
            "name": "Match Center foundation",
            "state": "COMPLETED" if complete("engines/match_context_engine.py", "templates/components/v944_match_center.html") else "PENDING",
            "evidence": "MatchContext y componentes canónicos",
        },
        {
            "name": "Match Center intelligence",
            "state": "COMPLETED"
            if complete(
                "engines/match_context_engine.py",
                "engines/match_live_story_engine.py",
                "engines/api_football_live_tracker_engine.py",
                "templates/components/v944_match_center.html",
                "tests/test_sports_core_match_center_intelligence.py",
            )
            else "PENDING",
            "evidence": "Datos persistidos, cronología deduplicada, estadísticas reales y contexto SHARK con evidencia",
        },
        {
            "name": "Match Intelligence Engine",
            "state": "COMPLETED"
            if complete(
                "engines/match_intelligence_engine.py",
                "engines/match_context_engine.py",
                "engines/shark_context_presentation_engine.py",
                "engines/telegram_intelligence_engine.py",
                "tests/test_sports_core_match_intelligence_engine.py",
            )
            else "PENDING",
            "evidence": (
                "Contrato MATCH-INTELLIGENCE-EVIDENCE-V1 reutilizado por "
                "Match Center, SHARK y Telegram sin acciones externas"
            ),
        },
        {
            "name": "Live Story Engine",
            "state": "COMPLETED" if complete("engines/match_live_story_engine.py") else "PENDING",
            "evidence": "Eventos confirmados y contrato lifecycle story",
        },
        {
            "name": "Developer Operating System",
            "state": "COMPLETED" if complete("engines/project_operating_system_engine.py", "blueprints/developer_center.py") else "IN_PROGRESS",
            "evidence": "Inventario, calidad, build y arquitectura",
        },
        {
            "name": "SHARK distribuido",
            "state": "CONTRACT_READY" if complete("engines/sports_platform_contracts.py", "engines/shark_context_presentation_engine.py") else "PENDING",
            "evidence": "Context envelope sin llamadas automáticas",
        },
        {
            "name": "SHARK Intelligence Platform",
            "state": "COMPLETED"
            if complete(
                "engines/shark_intelligence_platform_engine.py",
                "templates/shark_intelligence_center.html",
                "tests/test_shark_intelligence_platform.py",
            )
            else "PENDING",
            "evidence": "Centro de inteligencia deportiva trazable; consume Sports Core, Sports Knowledge, Sports Graph y Match Intelligence sin IA generativa.",
        },        {
            "name": "User Intelligence Platform",
            "state": "COMPLETED"
            if complete(
                "engines/user_intelligence_platform_engine.py",
                "templates/user_intelligence_center.html",
                "tests/test_user_intelligence_platform.py",
            )
            else "PENDING",
            "evidence": "Perfil deportivo interno transparente; consentimiento, exportacion, reset, borrado y desactivacion sin IA generativa ni datos de terceros.",
        },
        {
            "name": "Sports Intelligence Gateway",
            "state": "COMPLETED"
            if complete(
                "engines/sports_intelligence_gateway_engine.py",
                "tests/test_sports_intelligence_gateway.py",
                "tools/check_sports_intelligence_gateway.py",
            )
            else "PENDING",
            "evidence": "Puerta legal de fuentes deportivas: registro, compliance, salud y evidencia antes de cualquier uso o conexion.",
        },
        {
            "name": "Decision Engine",
            "state": "COMPLETED"
            if complete(
                "engines/decision_engine.py",
                "tests/test_decision_engine.py",
                "tools/check_decision_engine.py",
            )
            else "PENDING",
            "evidence": "Motor evidence-first que organiza lo que sabemos, lo que falta, cambios, coincidencias, discrepancias, calidad y confianza sin IA, picks ni predicciones.",
        },        {
            "name": "Experience Platform",
            "state": "COMPLETED"
            if complete(
                "engines/experience_platform_engine.py",
                "tests/test_experience_platform.py",
                "tools/check_experience_platform.py",
            )
            else "PENDING",
            "evidence": "Auditoria read-only de experiencia, consistencia UX, navegacion y densidad visual para convertir la arquitectura existente en una experiencia mas clara sin tocar logica ni produccion.",
        },
        {
            "name": "Action Platform",
            "state": "COMPLETED"
            if complete(
                "templates/action_platform.html",
                "tests/test_action_platform.py",
                "tools/check_action_platform.py",
            )
            else "PENDING",
            "evidence": "Smart Home, favoritos, watchlist, alertas, briefing, recap, actividad e historial de decision reutilizan Sports Core, Decision Engine, SHARK, User Intelligence y Gateway sin IA ni predicciones.",
        },
        {
            "name": "Telegram asistente",
            "state": "CONTRACT_READY" if complete("engines/sports_platform_contracts.py", "engines/telegram_intelligence_engine.py") else "PENDING",
            "evidence": "Context envelope sin envíos automáticos",
        },
        {
            "name": "Communication & Messaging System",
            "state": "COMPLETED"
            if complete(
                "engines/telegram_message_formatter.py",
                "engines/telegram_delivery_engine.py",
                "tests/test_telegram_premium_communication_system.py",
                "reports/NEMESIS_COMMUNICATION_SYSTEM_REPORT.md",
            )
            else "PENDING",
            "evidence": "Sistema premium de mensajes Telegram: identidad, jerarquía, transparencia y QA sin cambiar envío, cron, dedupe, destinos ni seguridad.",
        },
        {
            "name": "Sports Memory y Sports Graph",
            "state": "CONTRACT_READY" if complete("engines/sports_platform_contracts.py") else "PENDING",
            "evidence": "Referencias, memoria y aristas con evidencia",
        },
        {
            "name": "Team Center",
            "state": "COMPLETED" if complete("engines/team_center_engine.py", "templates/team_detail.html") else "PENDING",
            "evidence": "Team Center Premium Club Experience consume Sports Knowledge y Sports Graph.",
        },
        {
            "name": "Competition Center",
            "state": "COMPLETED" if complete("engines/competition_center_engine.py", "templates/competition_detail.html") else "PENDING",
            "evidence": "Competition Center Premium League Intelligence consume Sports Knowledge y Sports Graph.",
        },
        {
            "name": "Player Center",
            "state": "COMPLETED"
            if complete(
                "engines/player_center_engine.py",
                "templates/player_detail.html",
                "tests/test_player_center_premium_experience.py",
            )
            else "PENDING",
            "evidence": "Player Center Premium Sports Identity consume Sports Core, Sports Knowledge, Sports Graph, SHARK Intelligence y User Intelligence sin modelo paralelo.",
        },        {
            "name": "Product Finalization Release Candidate",
            "state": "COMPLETED"
            if complete(
                "reports/PRODUCT_FINALIZATION_REPORT.md",
                "reports/EXPERIENCE_SCORE_REPORT.md",
                "reports/RELEASE_READINESS_REPORT.md",
                "reports/MASTER_PRODUCT_AUDIT.md",
                "tools/run_product_finalization_browser_qa.py",
            )
            else "PENDING",
            "evidence": "Auditoria comercial completa: Experience Score, Release Readiness y Browser QA 24 superficies x 3 viewports.",
        },
        {
            "name": "Release 1.0 Operations Center",
            "state": "COMPLETED"
            if complete(
                "engines/company_operations_center_engine.py",
                "templates/admin_operations_center.html",
                "tools/check_v938_company_operations_center.py",
                "reports/OPERATIONS_CENTER_REPORT.md",
                "reports/PRODUCTION_OPERATIONS_REPORT.md",
                "reports/OBSERVABILITY_REPORT.md",
                "reports/RELEASE_GATE_STATUS.md",
            )
            else "IN_PROGRESS",
            "evidence": "Operations Center interno consolida plataforma, Render, cron, Telegram, Stripe, DB, cache, observabilidad, seguridad y Release 1.0 sin acciones externas.",
        },
        {
            "name": "Product Excellence Sprint 01",
            "state": "COMPLETED"
            if complete(
                "reports/TOP100_SPRINT_01_REPORT.md",
                "reports/PRODUCT_EXCELLENCE_REPORT.md",
                "reports/UX_IMPROVEMENTS_REPORT.md",
                "tests/test_product_excellence_sprint_01.py",
            )
            else "IN_PROGRESS",
            "evidence": "10 mejoras TOP 100 de UX, conversion responsable, estados seguros y accesibilidad sin crear modulos nuevos.",
        },
        {
            "name": "Product Excellence Sprint 02",
            "state": "COMPLETED"
            if complete(
                "reports/TOP100_SPRINT_02_REPORT.md",
                "reports/PRODUCT_EXCELLENCE_SPRINT_02.md",
                "reports/UX_IMPROVEMENTS_SPRINT_02.md",
                "tests/test_product_excellence_sprint_02.py",
            )
            else "IN_PROGRESS",
            "evidence": "9 mejoras P1 del TOP 100: metodologia, soporte, cancelacion, privacidad, medicion honesta, estado de datos, primer favorito y recap nocturno.",
        },
        {
            "name": "Beta privada",
            "state": "BLOCKED_BY_CERTIFICATION",
            "evidence": "Requiere integración Git, Render y QA real autorizada",
        },
    ]
    current = next(
        (item["name"] for item in modules if item["state"] in {"IN_PROGRESS", "PENDING"}),
        "Certificación operativa",
    )
    current_index = next((index for index, item in enumerate(modules) if item["name"] == current), len(modules) - 1)
    next_name = modules[min(current_index + 1, len(modules) - 1)]["name"]
    return {
        "contract": "NEMESIS-PRODUCT-ROADMAP-V1",
        "current_sprint": current,
        "next_sprint": next_name,
        "modules": modules,
        "completed": [item["name"] for item in modules if item["state"] == "COMPLETED"],
        "pending": [item["name"] for item in modules if item["state"] not in {"COMPLETED", "CONTRACT_READY"}],
        "innovation_lab": {
            "state": "CONTROLLED",
            "purpose": "Convertir problemas reales en propuestas con evidencia, guardrails y aprobación humana.",
            "automatic_actions": ["inventariar", "clasificar", "crear checklist", "generar prompt"],
            "approval_required": ["código", "datos", "Telegram", "pagos", "push", "deploy"],
        },
    }


def build_developer_center_snapshot(
    project_root: str | Path,
    app_version: str,
    runtime: Mapping[str, Any] | None = None,
    *,
    registered_routes: Iterable[str] | None = None,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    static = dict(_static_snapshot(str(root), app_version))
    quality = _mapping(static.get("quality"))
    exact_duplicates = list(quality.get("exact_source_duplicates") or [])
    registered = sorted(set(str(route) for route in (registered_routes or [])))
    render_sha = _text(os.getenv("RENDER_GIT_COMMIT"), 80)
    render_service = bool(os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID"))
    return {
        "contract": OPERATING_SYSTEM_CONTRACT,
        "generated_at_madrid": datetime.now(MADRID).isoformat(timespec="seconds"),
        **static,
        "git": _git_snapshot(root),
        "render": {
            "state": "CONFIRMED" if render_service and render_sha else "NOT_CERTIFIED",
            "environment_detected": render_service,
            "deployed_sha": render_sha,
            "note": (
                "Runtime Render detectado por variables de plataforma."
                if render_service
                else "La ejecución local no certifica el estado de Render."
            ),
        },
        "runtime": {
            "state": "CONFIRMED" if runtime else "NOT_CERTIFIED",
            "version": app_version,
            "flags": {
                key: value
                for key, value in _mapping(runtime).items()
                if str(key).startswith("has_") and isinstance(value, bool)
            },
        },
        "registered_routes": {
            "count": len(registered) if registered else None,
            "state": "CONFIRMED" if registered else "NOT_CERTIFIED",
        },
        "roadmap": build_product_roadmap(root),
        "build": _archive_status(root),
        "summary": {
            "exact_duplicate_groups": len(exact_duplicates),
            "route_duplicates": len(_mapping(static.get("routes")).get("duplicates") or {}),
            "css_cross_file_selectors": _mapping(quality.get("css")).get("cross_file_selectors", 0),
            "html_duplicate_groups": len(_mapping(quality.get("templates")).get("exact_duplicate_groups") or []),
        },
        "guardrails": {
            "external_calls": False,
            "database_writes": False,
            "secrets_returned": False,
            "automatic_push": False,
            "automatic_deploy": False,
        },
    }


def build_company_board_snapshot(
    project_root: str | Path,
    app_version: str,
    runtime: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    developer = build_developer_center_snapshot(project_root, app_version, runtime)
    quality = developer["quality"]
    git = developer["git"]
    roadmap = developer["roadmap"]
    sports = developer["sports_platform"]
    exact_duplicate_count = len(quality["exact_source_duplicates"])
    areas = [
        {
            "name": "Producto",
            "state": "CONFIRMED",
            "evidence": "Product Bible, Sports UX Bible y roadmap operativo presentes.",
            "next_action": roadmap["current_sprint"],
            "href": "/admin/ceo-dashboard",
        },
        {
            "name": "Arquitectura",
            "state": "REQUIRES_REVIEW" if exact_duplicate_count else "CONFIRMED",
            "evidence": f"{developer['file_stats']['engines']} motores y {exact_duplicate_count} grupos duplicados exactos.",
            "next_action": "Consolidar únicamente duplicados demostrados.",
            "href": "/admin/developer-center",
        },
        {
            "name": "UX",
            "state": "CONFIRMED",
            "evidence": "Calendario y Match Center consumen contratos canónicos.",
            "next_action": "Mantener Browser QA desktop, tablet y móvil.",
            "href": "/calendar",
        },
        {
            "name": "SHARK",
            "state": "PARTIALLY_VERIFIED",
            "evidence": "Motores y contrato de contexto presentes; calidad real depende de datos certificados.",
            "next_action": "Distribuir contexto solo tras certificar evidencia.",
            "href": "/admin/shark-ai",
        },
        {
            "name": "Telegram",
            "state": "NOT_CERTIFIED",
            "evidence": "Inteligencia y guardrails locales presentes; ningún envío real se prueba aquí.",
            "next_action": "Mantener dry-run hasta autorización de producción.",
            "href": "/admin/telegram/command-center",
        },
        {
            "name": "IA",
            "state": "PARTIALLY_VERIFIED",
            "evidence": "Gobernanza local disponible; proveedor y resultados reales no certificados.",
            "next_action": "Medir utilidad con datos reales antes de automatizar decisiones.",
            "href": "/admin/company-intelligence",
        },
        {
            "name": "Empresa",
            "state": "CONFIRMED",
            "evidence": "Operations Center, Release Gate, Company Intelligence, Sentinel y AutoPilot presentes.",
            "next_action": "Cerrar los bloqueos Release 1.0 con evidencia: Render, Telegram, Stripe, persistencia, UX y observabilidad.",
            "href": "/admin/operations-center",
        },
        {
            "name": "Calidad",
            "state": "REQUIRES_REVIEW" if quality["css"]["cross_file_selectors"] else "CONFIRMED",
            "evidence": (
                f"{quality['css']['cross_file_selectors']} selectores CSS cruzados requieren revisión visual; "
                f"{len(quality['templates']['exact_duplicate_groups'])} grupos HTML exactos."
            ),
            "next_action": "Reducir deuda solo con pruebas de regresión.",
            "href": "/admin/sentinel-autopilot",
        },
    ]
    risks = []
    if git["state"] != "CONFIRMED":
        risks.append(
            {
                "priority": "P0",
                "area": "Git",
                "title": "Main y carpeta oficial no están alineados",
                "evidence": git["summary"],
                "next_action": "Integrar ambos historiales mediante una operación Git autorizada y validada.",
            }
        )
    if exact_duplicate_count:
        risks.append(
            {
                "priority": "P1",
                "area": "Arquitectura",
                "title": "Implementaciones exactas duplicadas",
                "evidence": f"{exact_duplicate_count} grupos confirmados por SHA-256.",
                "next_action": "Mantener un módulo canónico y adaptadores mínimos cuando exista compatibilidad histórica.",
            }
        )
    if developer["render"]["state"] != "CONFIRMED":
        risks.append(
            {
                "priority": "P1",
                "area": "Producción",
                "title": "Render no certificado desde esta ejecución",
                "evidence": developer["render"]["note"],
                "next_action": "Certificar SHA, runtime y rutas después de un despliegue autorizado.",
            }
        )
    if quality["css"]["cross_file_selectors"]:
        risks.append(
            {
                "priority": "P2",
                "area": "Frontend",
                "title": "Cascada CSS extensa",
                "evidence": f"{quality['css']['cross_file_selectors']} selectores aparecen en más de un archivo.",
                "next_action": "Consolidar por componente con Browser QA; no hacer purga masiva.",
            }
        )
    blockers = [risk for risk in risks if risk["priority"] in {"P0", "P1"}]
    return {
        "contract": OPERATING_SYSTEM_CONTRACT,
        "version": app_version,
        "generated_at_madrid": developer["generated_at_madrid"],
        "state": "BLOCKED" if any(item["priority"] == "P0" for item in risks) else "CONTROLLED",
        "areas": areas,
        "risks": risks,
        "blockers": blockers,
        "next_priority": risks[0]["next_action"] if risks else roadmap["current_sprint"],
        "roadmap": roadmap,
        "sports_platform": sports,
        "developer_summary": developer["summary"],
        "git": git,
        "render": developer["render"],
        "guardrails": developer["guardrails"],
    }


def _archive_root_files(root: Path) -> list[Path]:
    files = []
    for path in root.iterdir():
        if not path.is_file():
            continue
        if path.name in ROOT_CONFIG or path.name in ROOT_DOCUMENTS or path.suffix.lower() == ".py":
            files.append(path)
    return files


def _archive_allowed(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    if any(part in GENERATED_DIRS | EVIDENCE_DIRS | DATA_DIRS for part in relative.parts):
        return False
    if path.name.lower() in ARCHIVE_FORBIDDEN_NAMES:
        return False
    if path.suffix.lower() in ARCHIVE_FORBIDDEN_SUFFIXES:
        return False
    if path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}:
        return False
    if path.name.startswith(".env") and path.name not in {".env.example"}:
        return False
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
        return relative.parts[0] == "static"
    return True


def _archive_candidates(root: Path) -> list[Path]:
    candidates = _archive_root_files(root)
    for directory in SOURCE_DIRS:
        base = root / directory
        if not base.exists():
            continue
        candidates.extend(path for path in base.rglob("*") if path.is_file())
    unique = {path.resolve(): path for path in candidates}
    return sorted(
        (path for path in unique.values() if _archive_allowed(path, root)),
        key=lambda path: _relative(path, root),
    )


def build_dev_source_archive(
    project_root: str | Path,
    app_version: str,
) -> dict[str, Any]:
    """Create a source-only archive after validating every entry."""

    root = Path(project_root).resolve()
    output_dir = (root / "release_output").resolve()
    if not _is_below(output_dir, root):
        raise ValueError("invalid_output_directory")
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "NeMeSiS_DEV_SOURCE.zip"
    candidates = _archive_candidates(root)
    entries = [_relative(path, root) for path in candidates]
    missing = sorted(ARCHIVE_REQUIRED - set(entries))
    forbidden = [
        entry
        for entry in entries
        if any(part in GENERATED_DIRS | EVIDENCE_DIRS | DATA_DIRS for part in Path(entry).parts)
        or Path(entry).suffix.lower() in ARCHIVE_FORBIDDEN_SUFFIXES
    ]
    if missing or forbidden:
        raise ValueError(
            json.dumps(
                {"missing_required": missing, "forbidden_entries": forbidden[:20]},
                ensure_ascii=False,
            )
        )
    manifest = {
        "contract": OPERATING_SYSTEM_CONTRACT,
        "version": app_version,
        "created_at_madrid": datetime.now(MADRID).isoformat(timespec="seconds"),
        "source_files": len(entries),
        "source_bytes": sum(path.stat().st_size for path in candidates),
        "excluded": sorted(GENERATED_DIRS | EVIDENCE_DIRS | DATA_DIRS),
        "forbidden_count": 0,
        "missing_required_root": [],
        "production_modified": False,
    }
    temp_handle = tempfile.NamedTemporaryFile(
        prefix="nemesis_dev_source_",
        suffix=".zip",
        dir=output_dir,
        delete=False,
    )
    temp_path = Path(temp_handle.name)
    temp_handle.close()
    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in candidates:
                archive.write(path, _relative(path, root))
            archive.writestr(
                "DEV_SOURCE_MANIFEST.json",
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            )
        temp_path.replace(output)
    finally:
        if temp_path.exists():
            temp_path.unlink()
    clear_project_snapshot_cache()
    return {
        **manifest,
        "path": _relative(output, root),
        "bytes": output.stat().st_size,
        "sha256": _hash_file(output),
        "available": True,
    }
