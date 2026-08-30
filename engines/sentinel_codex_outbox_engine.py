"""Codex outbox writer for Autonomous Company Sentinel."""
from __future__ import annotations

from pathlib import Path
from typing import Any


SENTINEL_CODEX_OUTBOX_VERSION = "V902_SENTINEL_FULL_ACTIVE_ISSUES_FIX_AND_TRUTH_CLEANUP_FINAL"

FALSE_POSITIVE_STATUSES = {
    "FALSE_POSITIVE",
    "DUPLICATE",
}

ARCHIVED_STATUSES = {
    "RESOLVED",
    "FIXED_PENDING_VERIFICATION",
    "EXTERNAL_BLOCKER",
    "INSUFFICIENT_EVIDENCE",
}

STALE_STATUSES = {
    "STALE",
}


def company_sentinel_outbox_dir(root: str | Path) -> Path:
    return Path(root) / "data" / "runtime" / "autonomous_company_sentinel" / "outbox"


def build_codex_prompt(issue: dict[str, Any]) -> str:
    return str(issue.get("codex_prompt") or "").strip() or (
        "Corrige esta incidencia en NeMeSiS SHARK PRO sin romper nada anterior.\n\n"
        f"ID:\n{issue.get('id') or 'SENT-PENDING'}\n\n"
        f"Area:\n{issue.get('area') or 'general'}\n\n"
        f"Severidad:\n{issue.get('severity') or 'low'}\n\n"
        f"Problema:\n{issue.get('title') or 'Incidencia pendiente de revisar'}\n\n"
        f"Evidencia:\n{issue.get('evidence') or 'Sin evidencia adicional'}\n\n"
        f"Ruta afectada:\n{issue.get('route') or 'Sin ruta concreta'}\n\n"
        f"Rol afectado:\n{issue.get('role') or issue.get('profile') or 'No especificado'}\n\n"
        f"Dispositivo afectado:\n{issue.get('device') or 'No especificado'}\n\n"
        f"Archivo probable:\n{issue.get('file') or 'Por determinar'}\n\n"
        "Reglas obligatorias:\n"
        "* No inventar datos.\n"
        "* No tocar secretos.\n"
        "* No romper usuarios, sesiones, membresias, pagos, DB_PATH, Madrid Time, Render Cron ni Telegram dedupe.\n"
        "* Mantener navegacion cliente/admin separada.\n"
        "* Mantener cliente PC con sidebar y cliente movil con bottom nav.\n"
        "* No enviar Telegram real.\n"
        "* No hacer pagos reales.\n"
        "* No hacer push/deploy automatico.\n\n"
        "Validaciones obligatorias:\n"
        "* python -m py_compile app.py\n"
        "* python tools/run_continuous_sentinel_static.py\n\n"
        "Entrega esperada:\n"
        "* resumen de cambios;\n"
        "* archivos tocados;\n"
        "* checks pasados;\n"
        "* limitaciones honestas;\n"
        "* estado Render real.\n"
    )


def _issue_id(issue: dict[str, Any]) -> str:
    return str(issue.get("id") or issue.get("issue_id") or "SENT-PENDING").replace("/", "-")


def _status(issue: dict[str, Any]) -> str:
    return str(issue.get("status") or "INSUFFICIENT_EVIDENCE").upper()


def _codex_eligible(issue: dict[str, Any]) -> bool:
    return (
        _status(issue) == "OPEN_REAL"
        and issue.get("evidence_sufficient") is True
        and bool(str(issue.get("evidence") or "").strip())
    )


def _tags(issue: dict[str, Any]) -> set[str]:
    raw = issue.get("tags") or []
    if isinstance(raw, str):
        raw = [raw]
    return {str(item).lower() for item in raw}


def _area(issue: dict[str, Any]) -> str:
    return str(issue.get("area") or issue.get("category") or "").lower()


def _is_reference_gap(issue: dict[str, Any]) -> bool:
    issue_id = _issue_id(issue)
    tags = _tags(issue)
    area = _area(issue)
    return "reference_gap" in tags or area in {"reference_visual", "visual_reference"} or issue_id.startswith("REFGAP-")


def _bucket_for_issue(issue: dict[str, Any]) -> str:
    status = _status(issue)
    area = _area(issue)
    tags = _tags(issue)
    if status in FALSE_POSITIVE_STATUSES:
        return "false_positive"
    if status in ARCHIVED_STATUSES:
        return "archived"
    if _is_reference_gap(issue):
        return "visual"
    if status in STALE_STATUSES:
        return "archived"
    if area.startswith("admin") or "admin" in tags:
        return "admin"
    if "telegram" in area or "telegram" in tags:
        return "telegram"
    if area in {"navigation", "copy", "sports_data", "picks_odds", "live", "payments", "logos", "shark_ai", "visual_layout"}:
        return "functional"
    return "active"


def _archive_line(issue: dict[str, Any]) -> str:
    return (
        f"- {_issue_id(issue)} | {_status(issue)} | "
        f"{issue.get('route') or issue.get('screen') or 'Sin ruta'} | "
        f"{issue.get('title') or 'Incidencia sin titulo'}"
    )


def write_codex_outbox(root: str | Path, issues: list[dict[str, Any]], archived_issues: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    outbox = company_sentinel_outbox_dir(root)
    outbox.mkdir(parents=True, exist_ok=True)
    prompts = []
    visual_prompts = []
    functional_prompts = []
    admin_prompts = []
    telegram_prompts = []
    false_positive_lines = []
    files = []
    for issue in issues:
        if not _codex_eligible(issue):
            continue
        issue_id = _issue_id(issue)
        prompt = build_codex_prompt(issue)
        path = outbox / f"{issue_id}_codex_prompt.md"
        path.write_text(prompt, encoding="utf-8")
        files.append(str(path))
        block = f"# {issue_id}\n\n{prompt}"
        bucket = _bucket_for_issue(issue)
        if bucket == "visual":
            visual_prompts.append(block)
            prompts.append(block)
        elif bucket == "admin":
            admin_prompts.append(block)
            prompts.append(block)
        elif bucket == "telegram":
            telegram_prompts.append(block)
            prompts.append(block)
        elif bucket == "functional":
            functional_prompts.append(block)
            prompts.append(block)
        elif bucket == "false_positive":
            false_positive_lines.append(_archive_line(issue))
        else:
            prompts.append(block)
    archived_issues = archived_issues or []
    archived_lines = []
    for issue in archived_issues:
        issue_id = _issue_id(issue)
        status = _status(issue)
        if status in FALSE_POSITIVE_STATUSES:
            false_positive_lines.append(_archive_line(issue))
        else:
            archived_lines.append(_archive_line(issue))

    sections = [
        ("ACTIVE_FIX_PROMPTS", prompts, "Sin prompts activos reproducidos."),
        ("VISUAL_REFERENCE_PROMPTS", visual_prompts, "Sin prompts visuales activos."),
        ("FUNCTIONAL_PROMPTS", functional_prompts, "Sin prompts funcionales activos."),
        ("ADMIN_PROMPTS", admin_prompts, "Sin prompts admin activos."),
        ("TELEGRAM_PROMPTS", telegram_prompts, "Sin prompts Telegram activos."),
        ("ARCHIVED_OBSOLETE_PROMPTS", archived_lines, "Sin prompts archivados."),
        ("FALSE_POSITIVE_PROMPTS", false_positive_lines, "Sin falsos positivos pendientes."),
    ]
    combined = "\n".join(
        f"\n\n## {title}\n\n" + ("\n\n---\n\n".join(content) if content else empty)
        for title, content, empty in sections
    )
    combined_path = outbox / "codex_outbox.md"
    combined_path.write_text(combined, encoding="utf-8")
    runtime_copy = Path(root) / "data" / "runtime" / "autonomous_company_sentinel" / "codex_outbox.md"
    runtime_copy.parent.mkdir(parents=True, exist_ok=True)
    runtime_copy.write_text(combined, encoding="utf-8")
    return {
        "engine_version": SENTINEL_CODEX_OUTBOX_VERSION,
        "prompt_count": len(prompts),
        "active_prompt_count": len(prompts),
        "visual_prompt_count": len(visual_prompts),
        "functional_prompt_count": len(functional_prompts),
        "admin_prompt_count": len(admin_prompts),
        "telegram_prompt_count": len(telegram_prompts),
        "archived_prompt_count": len(archived_lines),
        "false_positive_prompt_count": len(false_positive_lines),
        "files": files,
        "combined_path": str(combined_path),
        "runtime_copy": str(runtime_copy),
    }
