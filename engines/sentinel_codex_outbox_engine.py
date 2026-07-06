"""V892 Codex outbox writer for Autonomous Company Sentinel."""
from __future__ import annotations

from pathlib import Path
from typing import Any


SENTINEL_CODEX_OUTBOX_VERSION = "V900_REFERENCE_IMAGES_IMPORT_FIRST_REAL_VISUAL_GAP_AUDIT_FINAL"


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


def write_codex_outbox(root: str | Path, issues: list[dict[str, Any]], archived_issues: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    outbox = company_sentinel_outbox_dir(root)
    outbox.mkdir(parents=True, exist_ok=True)
    prompts = []
    visual_prompts = []
    functional_prompts = []
    files = []
    for issue in issues:
        issue_id = str(issue.get("id") or "SENT-PENDING").replace("/", "-")
        prompt = build_codex_prompt(issue)
        path = outbox / f"{issue_id}_codex_prompt.md"
        path.write_text(prompt, encoding="utf-8")
        files.append(str(path))
        block = f"# {issue_id}\n\n{prompt}"
        prompts.append(block)
        tags = set(issue.get("tags") or [])
        area = str(issue.get("area") or "")
        if "reference_gap" in tags or area == "reference_visual":
            visual_prompts.append(block)
        else:
            functional_prompts.append(block)
    archived_issues = archived_issues or []
    archived_lines = []
    for issue in archived_issues:
        tags = set(issue.get("tags") or [])
        area = str(issue.get("area") or "")
        status = str(issue.get("status") or "")
        issue_id = str(issue.get("id") or "SENT-PENDING").replace("/", "-")
        is_reference_gap = "reference_gap" in tags or area == "reference_visual" or issue_id.startswith("REFGAP-")
        should_reactivate = is_reference_gap and status in {"STALE_NEEDS_REVALIDATION", "NEEDS_REVALIDATION"}
        if should_reactivate:
            prompt = build_codex_prompt(issue)
            path = outbox / f"{issue_id}_codex_prompt.md"
            path.write_text(prompt, encoding="utf-8")
            files.append(str(path))
            block = f"# {issue_id}\n\n{prompt}"
            prompts.append(block)
            visual_prompts.append(block)
            continue
        archived_lines.append(
            f"- {issue.get('id') or 'SIN-ID'} | {issue.get('status') or 'ARCHIVED'} | "
            f"{issue.get('route') or 'Sin ruta'} | {issue.get('title') or 'Incidencia obsoleta'}"
        )
    active_section = "\n\n## Prompts activos\n\n" + ("\n\n---\n\n".join(prompts) if prompts else "Sin prompts Codex pendientes.")
    visual_section = "\n\n## Prompts visuales / referencia\n\n" + ("\n\n---\n\n".join(visual_prompts) if visual_prompts else "Sin prompts visuales activos.")
    functional_section = "\n\n## Prompts funcionales / producto\n\n" + ("\n\n---\n\n".join(functional_prompts) if functional_prompts else "Sin prompts funcionales activos.")
    archived_section = (
        "\n\n## Prompts archivados / obsoletos\n\n" + "\n".join(archived_lines)
        if archived_lines else "\n\n## Prompts archivados / obsoletos\n\nSin prompts archivados."
    )
    combined = active_section + visual_section + functional_section + archived_section
    combined_path = outbox / "codex_outbox.md"
    combined_path.write_text(combined, encoding="utf-8")
    runtime_copy = Path(root) / "data" / "runtime" / "autonomous_company_sentinel" / "codex_outbox.md"
    runtime_copy.parent.mkdir(parents=True, exist_ok=True)
    runtime_copy.write_text(combined, encoding="utf-8")
    return {
        "engine_version": SENTINEL_CODEX_OUTBOX_VERSION,
        "prompt_count": len(prompts),
        "visual_prompt_count": len(visual_prompts),
        "functional_prompt_count": len(functional_prompts),
        "archived_prompt_count": len(archived_lines),
        "files": files,
        "combined_path": str(combined_path),
        "runtime_copy": str(runtime_copy),
    }
