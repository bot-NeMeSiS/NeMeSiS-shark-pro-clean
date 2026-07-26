"""Non-destructive recovery scenario simulator for V939."""

from __future__ import annotations

from pathlib import Path
from typing import Any


SCENARIOS: dict[str, dict[str, Any]] = {
    "render_down": {"label": "Render caido", "rto_minutes": 60, "rpo_minutes": 15, "detection": ["external_health", "5xx_monitor"], "steps": ["confirmar alcance", "activar comunicacion", "validar ultimo release estable", "rollback autorizado si procede"]},
    "database_unavailable": {"label": "DB no disponible", "rto_minutes": 30, "rpo_minutes": 5, "detection": ["db_health", "application_errors"], "steps": ["detener escrituras", "comprobar disco y DB_PATH", "liberar lock seguro", "validar integridad"]},
    "database_corrupt": {"label": "DB corrupta", "rto_minutes": 120, "rpo_minutes": 60, "detection": ["integrity_check", "read_failures"], "steps": ["aislar DB", "preservar evidencia", "restaurar solo en entorno aislado", "autorizar restore"]},
    "sports_provider_down": {"label": "API deportiva caida", "rto_minutes": 240, "rpo_minutes": 60, "detection": ["sync_age", "provider_errors"], "steps": ["activar cache seguro", "marcar stale", "aplicar backoff", "reintentar dentro del usage guard"]},
    "telegram_down": {"label": "Telegram caido", "rto_minutes": 240, "rpo_minutes": 0, "detection": ["delivery_failures", "cron_health"], "steps": ["pausar cola", "preservar dedupe", "validar destino enmascarado", "reanudar con autorizacion"]},
    "stripe_webhook_down": {"label": "Webhook Stripe caido", "rto_minutes": 60, "rpo_minutes": 0, "detection": ["webhook_errors", "membership_mismatch"], "steps": ["bloquear cambios manuales no auditados", "validar firma y endpoint", "reconciliar eventos idempotentes"]},
    "cron_stopped": {"label": "Cron detenido", "rto_minutes": 60, "rpo_minutes": 60, "detection": ["last_tick_age", "dead_man_alert"], "steps": ["confirmar servicio", "comprobar header protegido", "ejecutar dry-run", "reanudar una sola instancia"]},
    "backup_stale": {"label": "Backup stale", "rto_minutes": 240, "rpo_minutes": 1440, "detection": ["backup_age", "restore_test"], "steps": ["preservar ultimo backup", "crear backup autorizado", "probar restore aislado", "registrar hash"]},
    "defective_release": {"label": "Release defectuoso", "rto_minutes": 30, "rpo_minutes": 0, "detection": ["runtime_sha", "smoke", "5xx"], "steps": ["detener rollout", "comparar SHA", "volver al commit estable", "revalidar runtime"]},
    "secret_revoked": {"label": "Secreto revocado", "rto_minutes": 120, "rpo_minutes": 0, "detection": ["auth_failures", "provider_status"], "steps": ["identificar integracion", "revocar/rotar manualmente", "actualizar entorno autorizado", "validar sin imprimir"]},
    "primary_operator_loss": {"label": "Operador principal no disponible", "rto_minutes": 240, "rpo_minutes": 60, "detection": ["operator_checkin", "runbook_access"], "steps": ["activar segundo operador", "usar runbooks", "verificar acceso minimo", "registrar decisiones"]},
}


def simulate_recovery_scenario(
    scenario_id: str,
    *,
    operations_evidence: dict[str, Any] | None = None,
    recovery_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    definition = SCENARIOS.get(str(scenario_id))
    if not definition:
        return {"ok": False, "scenario_id": scenario_id, "certification_state": "REQUIRES_REVIEW", "error": "unknown_scenario", "actions_executed": []}
    evidence = {"operations": operations_evidence or {}, "recovery": recovery_evidence or {}}
    available = bool(operations_evidence or recovery_evidence)
    return {
        "ok": True,
        "scenario_id": scenario_id,
        **definition,
        "certification_state": "PARTIALLY_VERIFIED" if available else "NOT_CERTIFIED",
        "evidence": evidence,
        "blockers": [] if available else ["No se aporto evidencia operacional para certificar los pasos."],
        "next_action": "Ejecutar tabletop review y validar el runbook en un entorno aislado.",
        "simulation_only": True,
        "restore_executed": False,
        "database_written": False,
        "external_calls": 0,
        "actions_executed": [],
    }


def build_recovery_simulator_snapshot(
    root: str | Path,
    db_path: str | Path,
    app_version: str,
    environment: str = "local",
) -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    try:
        from engines.disaster_recovery_engine import build_disaster_recovery_readiness

        readiness = build_disaster_recovery_readiness(root, db_path, app_version)
        evidence = {
            "ok": bool(readiness.get("ok")),
            "backup_count": readiness.get("backup_count", 0),
            "database": readiness.get("database", {}),
            "production_database_touched": readiness.get("production_database_touched", False),
        }
    except Exception as exc:
        evidence = {"ok": False, "safe_error_type": exc.__class__.__name__}
    scenarios = [simulate_recovery_scenario(key, recovery_evidence=evidence) for key in SCENARIOS]
    certified = sum(1 for item in scenarios if item.get("certification_state") == "PARTIALLY_VERIFIED")
    return {
        "version": app_version,
        "environment": environment,
        "certification_state": "PARTIALLY_VERIFIED" if evidence.get("ok") else "NOT_CERTIFIED",
        "confidence": 0.6 if evidence.get("ok") else None,
        "readiness_evidence": evidence,
        "scenarios": scenarios,
        "counts": {"total": len(scenarios), "with_local_evidence": certified, "production_certified": 0},
        "simulation_only": True,
        "restore_executed": False,
        "production_modified": False,
        "limitations": [
            "RTO y RPO son objetivos de gobierno, no tiempos demostrados.",
            "Ningun restore ni failover se ejecuta desde este motor.",
        ],
    }

