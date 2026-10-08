"""Presentation of existing master evidence; opening a priority executes nothing."""
from datetime import datetime


STEPS = {
    "db": ("Comprobar la lectura de la base de datos", "Revisa el diagnóstico y la última copia disponible antes de intervenir.", "/admin/data-vault"),
    "settings": ("Revisar la configuración", "Comprueba los ajustes que no se pudieron leer.", "/admin/dashboard"),
    "api_football": ("Revisar API-Football", "Consulta la respuesta y su fecha; distingue restricciones de acceso, caché y llamadas nuevas.", "/admin/data-center"),
    "sportsdb": ("Revisar TheSportsDB", "Consulta la última respuesta y los límites del proveedor.", "/admin/data-center"),
    "the_odds": ("Revisar las cuotas", "Comprueba si la evidencia procede de una llamada nueva o de caché.", "/admin/data-center"),
    "jobs": ("Revisar automatizaciones", "Abre la ejecución afectada y su resultado antes de preparar un reintento.", "/admin/daily-automation"),
    "telegram": ("Revisar entregas de Telegram", "Comprueba los fallidos y sus destinatarios antes de proponer un reintento.", "/admin/telegram/command-center"),
    "sentinel": ("Revisar incidencias abiertas", "Contrasta la evidencia de cada incidencia antes de cerrarla.", "/admin/sentinel-issues"),
    "sports": ("Comprobar la agenda", "Revisa la fecha, la cobertura y la última sincronización de partidos.", "/admin/data-center"),
}


def build_daily_priorities(areas, providers=(), *, job_at=None, sentinel_at=None):
    observed = {p.get("key"): p.get("observed_at") for p in providers}
    observed.update(jobs=job_at, sentinel=sentinel_at)
    entries = []
    seen = set()
    for area in areas:
        key, state = area.get("key"), area.get("state")
        if key not in STEPS or key in seen or state not in ("ATENCIÓN", "SIN DATOS"):
            continue
        seen.add(key)
        # Unknown routine status alone is not a new incident. Keep only unknown
        # core reads, whose failure otherwise disappears from recommendations.
        if state == "SIN DATOS" and key not in ("db", "settings", "sports"):
            continue
        title, step, href = STEPS[key]
        stamp = observed.get(key)
        try:
            parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            stamp = parsed.isoformat() if parsed.tzinfo else None
        except (AttributeError, TypeError, ValueError):
            stamp = None
        entries.append({"key": key, "title": title, "evidence": area.get("detail"),
                        "next_step": step, "href": href, "observed_at": stamp,
                        "category": "Por comprobar" if state == "SIN DATOS" else "Requiere revisión"})
    order = {key: i for i, key in enumerate(STEPS)}
    entries.sort(key=lambda item: order[item["key"]])
    return entries
