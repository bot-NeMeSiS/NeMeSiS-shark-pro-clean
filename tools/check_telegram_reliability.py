#!/usr/bin/env python3
"""Auditoria V727 de fiabilidad Telegram sin enviar mensajes."""

from __future__ import annotations

import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"
REPORT_MD = REPORT_DIR / "TELEGRAM_RELIABILITY_AUDIT_V727.md"
REPORT_JSON = REPORT_DIR / "TELEGRAM_RELIABILITY_AUDIT_V727.json"
ROOT_REPORT_MD = ROOT / "TELEGRAM_RELIABILITY_AUDIT_V727.md"


def main() -> int:
    os.environ.setdefault("SECRET_KEY", "telegram-reliability-audit-local")
    os.environ.setdefault("BACKGROUND_JOBS_ENABLED", "false")
    os.environ.setdefault("SCHEDULER_ENABLED", "false")
    os.environ.setdefault("DB_PATH", str(ROOT / "data" / "telegram_reliability_audit.db"))
    os.environ.setdefault("AUTO_SEND_TELEGRAM_PICKS", os.getenv("AUTO_SEND_TELEGRAM_PICKS", "false"))
    os.environ.setdefault("AUTO_GENERATE_PICKS", os.getenv("AUTO_GENERATE_PICKS", "false"))
    sys.path.insert(0, str(ROOT))

    import app as app_module  # noqa: WPS433

    snapshot = app_module.telegram_reliability_snapshot(limit=80)
    dry = app_module.telegram_reliability_dry_run()
    routes = sorted(rule.rule for rule in app_module.app.url_map.iter_rules() if "telegram" in rule.rule.lower())
    diagnosis = snapshot.get("diagnosis") or {}
    report = {
        "ok": bool(snapshot.get("ok")),
        "version": app_module.APP_VERSION,
        "diagnosis": diagnosis,
        "counts": snapshot.get("counts", {}),
        "reason_counts": snapshot.get("reason_counts", {}),
        "limits": snapshot.get("limits", {}),
        "env": snapshot.get("env", {}),
        "routes": routes,
        "dry_run": {
            "would_send": dry.get("would_send"),
            "preview_available": bool(dry.get("message_preview")),
            "discarded": len(dry.get("discarded") or []),
            "candidates": len(dry.get("candidates") or []),
        },
    }

    REPORT_DIR.mkdir(exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# TELEGRAM RELIABILITY AUDIT V727",
        "",
        f"- Version: `{app_module.APP_VERSION}`",
        f"- Estado: `{diagnosis.get('status', 'UNKNOWN_ERROR')}`",
        f"- Severidad: `{diagnosis.get('severity', 'unknown')}`",
        f"- Explicacion: {diagnosis.get('explanation', 'Sin explicacion disponible.')}",
        f"- Que hacer: {diagnosis.get('action', 'Revisar Command Center.')}",
        "",
        "## Variables configuradas",
    ]
    for key, value in sorted((snapshot.get("env") or {}).items()):
        lines.append(f"- `{key}`: {'si' if value is True else 'no' if value is False else value}")
    lines.extend(["", "## Rutas Telegram encontradas"])
    for route in routes:
        lines.append(f"- `{route}`")
    lines.extend(["", "## Conteos"])
    for key, value in sorted((snapshot.get("counts") or {}).items()):
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Razones de descarte"])
    reasons = snapshot.get("reason_counts") or {}
    if reasons:
        for key, value in sorted(reasons.items(), key=lambda item: item[1], reverse=True):
            lines.append(f"- `{key}`: {value}")
    else:
        lines.append("- Sin descartes registrados en la muestra.")
    lines.extend(["", "## Limites y ventanas"])
    for key, value in sorted((snapshot.get("limits") or {}).items()):
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Dry-run"])
    lines.append(f"- Enviaria: {'si' if dry.get('would_send') else 'no'}")
    lines.append(f"- Candidatos: {len(dry.get('candidates') or [])}")
    lines.append(f"- Descartados: {len(dry.get('discarded') or [])}")
    lines.append(f"- Preview disponible: {'si' if dry.get('message_preview') else 'no'}")
    lines.extend(["", "## Nota"])
    lines.append("Este script no envia mensajes Telegram, no muestra secrets y no requiere trafico real.")

    markdown = "\n".join(lines) + "\n"
    REPORT_MD.write_text(markdown, encoding="utf-8")
    ROOT_REPORT_MD.write_text(markdown, encoding="utf-8")
    print(json.dumps({"ok": True, "report": str(REPORT_MD), "status": diagnosis.get("status")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
