"""Closed provider evidence shared by sync receipts and read-only admin views."""
from datetime import datetime


FAILURE_PRIORITY = (
    "ACCOUNT_SUSPENDED", "AUTH_OR_ACCESS", "ACCESS_RESTRICTED",
    "RATE_OR_QUOTA", "NETWORK_OR_TIMEOUT", "FREE_PLAN_SEASON_RESTRICTED",
    "SEASON_UNAVAILABLE", "FREE_PLAN_RESTRICTED", "ENDPOINT_RESTRICTED",
    "COVERAGE_UNAVAILABLE", "SUBSCRIPTION_RESTRICTED", "PLAN_OR_COVERAGE_OTHER",
    "PLAN_OR_COVERAGE", "PROVIDER_RESPONSE", "UNKNOWN_PROVIDER_ERROR",
)


def safe_failure_categories(values):
    if not isinstance(values, (list, tuple)):
        values = [values]
    found = {value for value in values if isinstance(value, str)}
    return [category for category in FAILURE_PRIORITY if category in found]


def provider_stage_evidence(stage):
    """Project known codes only; never forward provider messages or infer billing."""
    stage = stage if isinstance(stage, dict) else {}
    values = safe_failure_categories(stage.get("failure_categories"))
    values += safe_failure_categories(stage.get("failure_category"))
    state = str(stage.get("state") or stage.get("status") or "").upper()
    for prefix in ("PARTIAL_", "CACHE_PROVIDER_FAILURE_", "PROVIDER_FAILURE_BACKOFF_", "CACHE_"):
        if state.startswith(prefix):
            label = state[len(prefix):].split("_ERROR_KEY_", 1)[0]
            values += safe_failure_categories(label)
    # Older records identify the access field, without proving a suspension.
    if state.endswith("_ERROR_KEY_ACCESS") and "ACCOUNT_SUSPENDED" not in values:
        values.append("ACCESS_RESTRICTED")
    reason = stage.get("reason_code")
    if not (reason == "AUTH_OR_ACCESS" and "ACCOUNT_SUSPENDED" in values):
        values += safe_failure_categories(reason)
    categories = safe_failure_categories(values)
    reused = "CACHE" in state or "BACKOFF" in state or stage.get("cached_provider_failure") is True
    calls = stage.get("external_calls")
    whole_calls = ((isinstance(calls, int) and not isinstance(calls, bool))
                   or (isinstance(calls, float) and calls.is_integer()))
    current = (stage.get("provider_observation_current") is True
               and whole_calls
               and calls > 0 and not reused)
    observed_at = ""
    stamp = stage.get("provider_observed_at")
    if isinstance(stamp, str) and len(stamp) <= 40:
        try:
            parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                observed_at = parsed.isoformat(timespec="seconds")
        except ValueError:
            pass
    return {
        "failure_categories": categories,
        "failure_category": categories[0] if categories else "",
        "provider_observed_at": observed_at,
        "provider_observation_current": current,
        "observation_scope": "CURRENT_CYCLE" if current else "REUSED" if reused else "NOT_ESTABLISHED",
    }


def provider_failure_advice(category):
    if category == "ACCOUNT_SUSPENDED":
        return ("Suspensión comunicada", "Motivo sin confirmar: revisar el aviso y el consumo en la cuenta del proveedor.")
    if category in {"AUTH_OR_ACCESS", "ACCESS_RESTRICTED"}:
        return ("Acceso rechazado", "Revisar el aviso de acceso del proveedor; no se ha confirmado un problema de pago.")
    if category == "RATE_OR_QUOTA":
        return ("Límite de consultas", "Revisar el consumo y la hora de renovación del cupo antes de cambiar de plan.")
    if category == "NETWORK_OR_TIMEOUT":
        return ("Problema de conexión", "Comprobar el resultado del siguiente ciclo automático.")
    if category in {"FREE_PLAN_SEASON_RESTRICTED", "SEASON_UNAVAILABLE", "FREE_PLAN_RESTRICTED",
                    "ENDPOINT_RESTRICTED", "COVERAGE_UNAVAILABLE", "SUBSCRIPTION_RESTRICTED",
                    "PLAN_OR_COVERAGE_OTHER", "PLAN_OR_COVERAGE"}:
        return ("Cobertura o plan limitado", "Revisar fechas, competiciones y acceso incluidos en la suscripción; el rechazo no demuestra impago.")
    return ("Respuesta del proveedor pendiente de revisión", "Revisar el resultado registrado; no se ha confirmado la causa.")
