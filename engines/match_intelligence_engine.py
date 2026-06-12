"""Match Intelligence foundation based only on internal synced data."""
from __future__ import annotations


def build_match_intelligence(match: dict | None = None, picks: list[dict] | None = None) -> dict:
    match = dict(match or {})
    picks = picks or []
    home = match.get("home_team") or "Local"
    away = match.get("away_team") or "Visitante"
    status = str(match.get("status") or "").lower()
    score = match.get("score") or ""
    related = [p for p in picks if str(p.get("match_id") or "") == str(match.get("id") or "")]
    missing = []
    for key, label in [("competition_name", "competición"), ("kickoff_time", "hora"), ("status", "estado")]:
        if not match.get(key):
            missing.append(label)
    if "final" in status and score:
        summary = f"Partido finalizado: {home} vs {away}, marcador sincronizado {score}."
    elif match:
        summary = f"Previa interna para {home} vs {away} basada en datos sincronizados disponibles."
    else:
        summary = "Contexto pendiente de sincronización."
    return {
        "ok": True,
        "match_id": match.get("id"),
        "title": f"{home} vs {away}",
        "summary": summary,
        "shark_context": "SHARK usa calendario, picks relacionados y estado del partido cuando existen.",
        "risks": ["Datos incompletos" if missing else "Sin riesgos técnicos destacados con los datos actuales."],
        "signals": ["Pick relacionado disponible"] if related else ["Sin pick relacionado publicado."],
        "missing_data": missing,
        "related_picks": related[:5],
        "no_fake_data": True,
    }


def match_intelligence_snapshot() -> dict:
    return {
        "ok": True,
        "status": "MATCH_INTELLIGENCE_FOUNDATION_READY",
        "rules": [
            "No inventa noticias.",
            "No llama APIs externas en cada carga.",
            "Si faltan datos, muestra contexto pendiente de sincronización.",
        ],
    }
